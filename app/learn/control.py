from aiogram import types
from app.core import bot, authorize, get_session, RESTART
from bot_utils import to_one_row_keyboard, get_hint
from ilt import sort_words, tasks, level_up
import spaced_repetition as sr
import mysql_connect
from app.learn import reading
from loguru import logger

from speech import text2speech


async def start_learning_message(message):
    session, isValid = await authorize(message.from_user.id, with_lang=True)
    if not isValid:
        return
    if message.text == '/test':
        # FIXME do I need it? (Used in adding words to specify calls. Should be replaced with normal dp.callback_query_handler
        session.status = '/test'
    if message.text == '/learn':
        session.status = '/learn'
    await message.reply("OK, let's learn some " + session.active_lang())
    kb = to_one_row_keyboard(["10", "20", "30", "40", "All"],
                             data=[10, 20, 30, 40, 1000],
                             action=["start_learning"] * 5)
    await bot.send_message(session.get_user_id(), "How many words should I offer to you this time?",
                           reply_markup=kb)


async def learning(query: types.CallbackQuery, callback_data: dict):
    await query.answer("Let's learn!")
    logger.debug(query)
    logger.debug(str(query.from_user.id)
                 + "start_learning  " + str(callback_data))
    n = int(callback_data['data'])
    session, isValid = await authorize(query.from_user.id, with_lang=True)
    if not isValid:
        return
    if n > 0:  # 10, 20, 30, 40, 1000
        hids = list()
        if session.status == '/test':
            hids = sr.get_items_to_learn(
                (session.get_user_id(), session.active_lang()), upper_recall_limit=1.0, n=n)
        if session.status == '/learn':
            hids = sr.get_items_to_learn(
                (session.get_user_id(), session.active_lang()), upper_recall_limit=0.5, n=n)
        if len(hids) == 0:
            if session.status == '/test':
                await bot.send_message(session.get_user_id(),
                                       'You should add at least one word with /addwords command to start training')
            else:
                await bot.send_message(session.get_user_id(), 'You don\'t have words for training.')
                await bot.send_message(session.get_user_id(), 'Add more words with /addwords command or')
                await bot.send_message(session.get_user_id(), 'or /test words you learned before.')
            return True
    words = mysql_connect.fetch_by_hids(session.get_user_id(), hids)
    session.words_to_learn = words
    session.current_word = 0

    if not session.has_more_words_to_learn():
        # Case 2: doing reading errors
        await bot.send_message(session.get_user_id(), "Let's revise some words")
        await reading.do_reading_errors(query, callback_data)
    else:
        # Case 1: reading exercises
        await start_learning(query, callback_data, session)




# Get reply from the user and filter the data: set number and shuffle
async def start_learning(query: types.CallbackQuery, callback_data: dict, session):
    n = int(callback_data['data'])
    words = session.words_to_learn
    if n > len(words):
        await bot.send_message(session.get_user_id(), "You have only *" + str(len(words)) + "* words for this session")
    if n < len(words):
        words = words[:n]
    words = sort_words(words)
    session.words_to_learn = words
    await bot.send_message(session.get_user_id(), "Check if you remember these words")
    await do_learning(session)



# The learning loop, reading task 1
async def do_learning(session):
    session, isValid = await authorize(session.get_user_id())
    if not isValid:
        return
    await do_learning1(session)


async def do_learning1(session):
    if not session.has_more_words_to_learn():
        await reading.do_reading_errors1(session)
    else:
        session = await get_session(session.get_user_id())
        if session is None:
            return
        word = session.get_current_word()  # 0. word, 1. definition, 2. mode, 3. hid
        if word is None:
            await bot.send_message(session.get_user_id(), RESTART)
            logger.error(str(session.get_user_id()) + " word is None")
            return
        if word[2] == 0:
            # Do reading exercises
            keyboard = to_one_row_keyboard(["I remember", "Show meaning"],
                                           data=[0, 1],
                                           action=["I_remember", "show"])
            hint = get_hint(word[1])
            await bot.send_message(session.get_user_id(), '*' + word[0] + "*\n" + hint, reply_markup=keyboard)
        elif word[2] == 2:
            if session.subscribed:
                session.status = tasks[2]
                await bot.send_message(session.get_user_id(), "*SAY* this word: *" + word[1] + "*")
            else:
                level_up(session)
                await do_learning(session)
        elif word[2] == 3:
            if session.subscribed:
                session.status = tasks[2]
                await bot.send_message(session.get_user_id(), "*LISTEN* and *SAY* this word: *{}*\n{}".
                                       format(word[0], word[1]))
                voice = text2speech.get_voice(word[0], session.active_lang())
                await bot.send_audio(chat_id=session.get_user_id(),
                                     audio=voice,
                                     performer=word[1], caption=None,
                                     title=word[0])
            else:
                level_up(session)
                await do_learning(session)

        elif word[2] == 1:
            session.status = tasks[1]
            await bot.send_message(session.get_user_id(),
                                   "*WRITE* the correct word for the definition:\n*" + word[1] + "*")
