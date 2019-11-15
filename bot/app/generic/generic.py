import pickle
import sys

from loguru import logger
from aiogram import types

from bot.app.core import authorize, bot, sessions, get_session, LANGS
from bot.bot_utils.bot_utils import to_vertical_keyboard
from bot.session import Session
from bot.bot_utils import mysql_connect as db, mysql_connect, bot_utils

DEFINITION_SOURCES = ['Wiktionary', 'Yandex Dictionary', 'Google Translate']

help_text = 'Welcome!\n' \
            '1. Select language to learn with /setlanguage.\n' \
            '  The bot will try to show word definitions in your user language set in Telegram if possible.\n' \
            '  You can change your user language with /settings command\n' \
            '2. Then /addwords to get exercises.\n' \
            '  Or you can add many words with /addtext or /wordlist command.\n' \
            '3. Then type /learn to start training.\n' \
            '  - If you already learned some words, type /test\n' \
            '  - You can delete words with a /delete command\n\n' \
            '*/subscribe* to activate premium features (voice recognition, automatic translations ' \
            'and text-to-speech\n\n' \
            'To see the words that you already added:\n' \
            ' /show - shows all added words in alphabetical order\n' \
            ' /show _date_ - shows all added words starting from oldest to newly added\n' \
            ' /show _abc_ - shows all words that start with _abc_ \n' \
            ' /show _last N_ - shows last N added words (replace _N_ with an actual number)\n\n' \
            'To get help:\n' \
            '- Type /help if you want to see this text again\n' \
            '- Start typing "/" any time to access the commands from the list'


async def start_message(message: types.Message):
    if sys.argv[1:][0] == 'dev':
        await bot.send_message(message.from_user.id,
                               "*A T T E N T I O N !*\nThis is a testing bot. Do not use it for learning words!")
    logger.info(str(message.from_user.id) + ' /start command')
    s = Session(message.from_user.id, message.from_user.first_name, message.from_user.last_name,
                message.from_user.language_code)
    s.subscribed = db.check_subscribed(message.from_user.id)
    logger.info("{} subsctibtion status is {}", message.from_user.id, s.subscribed)
    if message.from_user.language_code is None:
        await bot.send_message(message.from_user.id,
                               "Your user language is not set. It means that all word definitions will be in English. Set your Telegram user language and /start the bot again.")
    db.update_user(message.from_user.id, message.from_user.first_name, message.from_user.last_name,
                   message.from_user.language_code)
    sessions[message.from_user.id] = s
    await message.reply(help_text)
    await bot.send_photo(message.from_user.id, types.InputFile('bot/menu1.1.png'))


async def help_message(message: types.Message):
    logger.info(str(message.from_user.id) + ' /help command')
    await message.reply(help_text)
    await bot.send_photo(message.from_user.id, types.InputFile('bot/menu1.1.png'))
    await bot.send_message(message.from_user.id, "*If you have questions, you can ask them at https://t.me/OppiWords*")


async def stop_message(message: types.Message):
    logger.info(str(message.from_user.id) + ' /stop command')
    session, isValid = await authorize(message.from_user.id, with_lang=True)
    if not isValid:
        return
    session.status = str()
    session.words_to_learn = list()
    session.read_error_storage = list()
    session.current_word = 0
    session.hid_cash = str()
    session.words_to_add = None
    session.definitions = list()
    session.list_hid_word = None  # ""(list_name, hid)
    await message.reply("You session is restarted.")

# SETTINGS ==================================================================
# TODO definition sources: Wiktionary, Yandex Dictionary, Google Translate
async def settings_message(message: types.Message):
    logger.info(str(message.from_user.id) + ' /settings command')
    session, isValid = await authorize(message.from_user.id, with_lang=True)
    if not isValid:
        return
    await bot.send_message(message.from_user.id, "A few settings to make.")
    await bot.send_message(message.from_user.id, "*If you have questions, you can ask them at https://t.me/OppiWords*")
    m = await bot.send_message(message.from_user.id,
                               "Please, specify the language in which you want to get definitions (e.g. Russian or German or any other language name) "
                               "of words and phrases", reply_markup=types.ForceReply())
    session.status = m.message_id + 1


async def set_user_language_message(message: types.Message):
    user_id = message.from_user.id
    logger.info(str(user_id) + ' /settings received')
    session = await get_session(user_id)
    if session is None:
        return
    if message.text.lower() not in LANGS:
        await message.reply("Sorry, can't recognize the language name. Make sure it's correct and is *in English* "
                            "(e.g. instead of _Deutsch_ use _German_).")
        return
    session.status = None
    session.language_code = message.text.lower()
    await bot.send_message(user_id, "The language is set to {}".format(str(session.language_code).title()))
    session.language_code = message.text.lower()
    with open('sessions.pkl', 'wb') as f:
        pickle.dump(sessions, f)
    session.def_sources = list()
    k = await source_keyb(list())
    is_supported = session.language_code in bot_utils.CODES.keys()
    s = 'but will give definitions in your language'
    if not is_supported:
        s = 'and unfortunately does not support ' + session.language_code.title()
    await bot.send_message(user_id, "Select what dictionaries you would like to use\n"
                                    "*Wiktionary* _(default)_ supports many languages, but definitions are only in English\n"
                                    "*Yandex Dictionary* is less accurate, {}\n"
                                    "*Google Translate* may be inaccurate for single words, but is often the only way to get a translation for a phrase"
                           .format(s),
                           reply_markup=k)


async def source_keyb(used_sources):
    data = list()
    buttons = list()
    for i in range(len(DEFINITION_SOURCES)):
        if DEFINITION_SOURCES[i] in used_sources:
            continue
        data.append(i)
        buttons.append(DEFINITION_SOURCES[i])
    actions = ['def_source'] * len(data)
    buttons.append("FINISH")
    data.append(-1)
    actions.append('def_source_finish')
    k = to_vertical_keyboard(buttons, data, actions)
    return k


async def def_source_action(query, callback_data):
    user_id = query.from_user.id
    logger.info(str(user_id) + ' def_source_action received')
    session = await get_session(user_id)
    if session is None:
        return
    def_source = DEFINITION_SOURCES[int(callback_data['data'])]
    logger.debug(str(user_id) + ' selected ' + def_source)
    session.def_sources.append(def_source)
    mysql_connect.insertone('INSERT INTO def_sources (user, source) '
                            'VALUES(%s, %s)', (user_id, def_source))
    k = await source_keyb(session.def_sources)
    await bot.edit_message_reply_markup(session.get_user_id(),
                                        query.message.message_id,
                                        reply_markup=k)

async def def_source_finish_action(query):
    user_id = query.from_user.id
    logger.info(str(user_id) + ' def_source_action_finish received')
    session = await get_session(user_id)
    if session is None:
        return
    for s in DEFINITION_SOURCES:
        if s not in session.def_sources:
            mysql_connect.deleteone('DELETE FROM def_sources WHERE user=%s AND source=%s',
                                    (user_id, s))
    if len(session.def_sources) == 0:
       await bot.edit_message_text("You didn't select any dictionary.\n"
                                   "{} is set as default".format(DEFINITION_SOURCES[0]), chat_id=session.get_user_id(),
                                        message_id=query.message.message_id)
    else:
        await bot.edit_message_text('OK, settings are saved', chat_id=session.get_user_id(),
                                        message_id=query.message.message_id)



# UNKNOWN ==================================================================
async def text_message(message):
    logger.debug(str(message.from_user.id)
                 + " Received message unknown message")
    logger.debug(str(message.from_user.id) + message.text)
    t = message.text
    buttons = ["Add word", "Search Wiktionary"]
    actions = ["add_user_definition", "wiktionary_search"]
    if str(t).lower() in LANGS:
        buttons.append("Set language")
        actions.append('setlanguage')
    buttons.append("CANCEL")
    actions.append("finish_adding_meanings")
    data = ['0'] * len(buttons)
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    session.words_to_add = (t,)
    k = to_vertical_keyboard(buttons, action=actions, data=data)
    await message.reply("What would you like to do with this word?", reply_markup=k)


async def unknow_query_handler(query: types.CallbackQuery):
    logger.info('Got this callback data: ', query.data)
    logger.info('Got this query.as_json: ', query.as_json())
    await query.answer("Don't know what to do))")
