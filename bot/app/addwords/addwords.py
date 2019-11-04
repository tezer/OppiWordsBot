import time

from loguru import logger
from aiogram import types
from app.core import authorize, bot, RESTART
from bot.bot_utils.bot_utils import to_one_row_keyboard, truncate, to_vertical_keyboard, get_definitions
from app.wordlist import wordlist
from bot.bot_utils import spaced_repetition as sr, mysql_connect


async def addwords_message(message):
    logger.info(str(message.from_user.id) + " started adding new words")
    command = str(message.text)
    session, isValid = await authorize(message.from_user.id, with_lang=True)
    if not isValid:
        return
    lists_to_add = mysql_connect.lists_to_add(
        message.from_user.id, session.active_lang())
    if len(lists_to_add) > 0:
        word_list = str(lists_to_add[0][0])
        session.list_hid_word = (word_list, None, None)
        k = to_one_row_keyboard(['Add words', 'Not now'], [0, 0], [
            "next_word_from_list", "skip_list"])
        await bot.send_message(message.from_user.id,
                               "You have words to add from list *{}*".format(
                                   word_list.title()),
                               reply_markup=k)
    else:
        session.status = "/addwords"
        session.words_to_add = None
        if command != "/addwords":
            logger.warning(str(message.from_user.id)
                           + " put words after /addwords ")
        logger.debug(str(message.from_user.id) + session.status)
        await message.reply("Type in words in *" + session.active_lang().title() + "*")



async def skip_list_action(query: types.CallbackQuery, callback_data: dict):
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    session.status = "/addwords"
    session.words_to_add = None
    session.list_hid_word = None
    logger.debug(str(query.from_user.id) + session.status)
    await bot.send_message(query.from_user.id, "Type in words in *" + session.active_lang().title() + "*")


# Getting a new word typed in by a user and getting definitions
async def wiktionary_search_action(query: types.CallbackQuery, callback_data: dict):
    message = query.message.reply_to_message
    await wiktionary_search(message)


async def wiktionary_search(message):
    logger.debug(str(message.from_user.id) + " Adding word: " + message.text)
    logger.info(str(message.from_user.id) + " Sending request to dictionaries")
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    begin = time.time()
    definitions = get_definitions(session.active_lang(), session.language_code, message.text)
    logger.info(str(session.get_user_id()) + " Received response from dictionaries "
                + str(time.time() - begin))
    logger.debug(str(session.get_user_id())
                 + " Received definitions: " + str(definitions))
    session.words_to_add = (message.text, definitions)
    if len(definitions) == 0:
        logger.info(str(session.get_user_id()) + " no definition found")
        await message.reply("No definitions found. Make sure there is no typos in the word and the language you're "
                            "learning exists))")
        kb = to_one_row_keyboard(["Add definition", "Skip"],
                                 data=[0, 1],
                                 action=["add_user_definition", "add_user_definition"])
        await bot.send_message(message.chat.id,
                               "Or you can add your own definition", reply_markup=kb)
    else:
        session.definitions = definitions
        await prepare_definition_selection(session, None)


async def add_word_to_storage(session, word, definition):
    # session.get_session()
    hid = sr.add_item(
        (session.get_user_id(), session.active_lang()), (word, definition), 0)
    mysql_connect.insert_word(session.get_user_id(), session.active_lang(),
                              word, definition, 0, hid)


# building up inline keybard
async def prepare_definition_selection(session, query):
    logger.debug(str(session.get_user_id()) + " prepare_definition_selection")
    definitions = session.definitions
    definitions = truncate(definitions,
                           30)  # FIXME ideally, it should be called once, not every time the keyboard is built
    actions = ['meaning'] * len(definitions)
    button_titiles = definitions
    data = list(range(0, len(actions), 1))

    actions.append('add_user_definition')
    button_titiles.append("ADD YOUR DEFINITION")
    data.append(0)

    if session.list_hid_word is None:
        button_titiles.append("CLOSE")
        actions.append('finish_adding_meanings')
        data.append(-1)
    else:
        button_titiles.append("NEXT")
        actions.append('next_word_from_list')
        data.append(-1)
        button_titiles.append("FINISH")
        actions.append('finish_adding_meanings')
        data.append(-1)

    # k = to_vertical_keyboard(definitions, action=actions, data=list(range(0, len(actions), 1)))
    k = to_vertical_keyboard(definitions, action=actions, data=data)
    if query is None:
        await bot.send_message(session.get_user_id(), "Tap a button with a meaning to learn", reply_markup=k,
                               parse_mode=types.ParseMode.MARKDOWN)
    else:
        await bot.edit_message_reply_markup(session.get_user_id(), query.message.message_id, reply_markup=k)


# Adding selected definition
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    logger.info(str(query.from_user.id)
                + ' Got this callback data: %r', callback_data)

    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return

    n = int(callback_data.get('data'))
    if session.words_to_add is not None:
        word = session.words_to_add[0]
    else:
        logger.error(str(session.get_user_id())
                     + ", session.words_to_add is None")
        await bot.send_message(session.get_user_id(), RESTART)
        return
    try:
        definition = session.words_to_add[1][n]
    except IndexError as e:
        logger.warning(e)
        await bot.send_message(session.get_user_id(), RESTART)
        return
    # session.words_to_add = None # Not needed for multiple definitions
    del session.definitions[n]
    logger.info(str(session.get_user_id()) + " Adding new word: "
                + word + " - " + definition)
    await add_word_to_storage(session, word, definition)
    await query.answer("Definition added")
    await prepare_definition_selection(session, query)


async def callback_add_user_definition_action(query: types.CallbackQuery, callback_data: dict):
    logger.debug(
        'callback_add_user_definition_action Got this callback data: %r', callback_data)
    await query.answer()
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    if callback_data.get('data') == "1":
        await bot.send_message(query.from_user.id, "OK, skipping")
        if session.list_hid_word is not None:
            await wordlist.adding_list_words(None, query, None)
    else:
        session.status = 'adding_user_definition'
        word = session.words_to_add[0]
        await bot.send_message(query.message.chat.id,
                               "Type in your definition for {}".format(word),
                               reply_markup=types.ForceReply())


async def adding_words(message):
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    definition = message.text
    if session.words_to_add is None:
        await bot.send_message(message.from_user.id,
                               "Sorry, cannot add the definition.\nPlease, use /addwords command first and *then* type words that you want to add in a new line.")
        return
    word = session.words_to_add[0]
    session.words_to_add = None
    logger.debug(word + ": " + definition)
    await add_word_to_storage(session=session,
                              word=word,
                              definition=definition)
    session.status = "/addwords"
    if session.list_hid_word is not None:
        await wordlist.adding_list_words(message, None, None)
    else:
        await bot.send_message(message.from_user.id, "OK")


async def finish_adding_meanings_action(query: types.CallbackQuery, callback_data: dict):
    logger.info(str(
        query.from_user.id) + ' Finished adding definitions. Got this callback data: %r', callback_data)
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    session.words_to_add = None
    session.definitions = list()
    session.status = "/addwords"
    session.adding_list = False
    await bot.edit_message_text(chat_id=session.get_user_id(), message_id=query.message.message_id,
                                text="OK. You can add more words. Or /learn the new ones.")
