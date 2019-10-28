import re

from aiogram import Bot, Dispatcher, executor, md, types
from aiogram.utils.exceptions import BotBlocked as Blocked, CantParseEntities
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.callback_data import CallbackData

import time
import random
import pickle
from pathlib import Path
import sys

import spaced_repetition as sr
from session import Session
from settings import bot_token
from settings import db_conf
from settings import admin
from bot_utils import get_definitions, get_hint, to_one_row_keyboard, truncate, \
    to_vertical_keyboard
import word_lists

import logging
import mysql_connect
import user_stat

RESTART = '"Sorry, something went wrong. Try restarting with /start, your progress is saved"'
LANGS = list()
logger = logging.getLogger('oppi_wiki_bot')
# hdlr = logging.StreamHandler()
hdlr = logging.FileHandler('bot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)

#
# help - get help
# start - start the bot and get help
# setlanguage - specify a language you want to learn. You can switch between languages or add new ones any time
# addwords - add words to learn
# wordlist - add a list of words (you will have to add definitions after adding the list)
# learn - learn the words you added
# test - test the words you learned
# show - show all added words in alphabetical order
# delete - delete a word form your dictionary
#


bot = Bot(token=bot_token[sys.argv[1:][0]],
          parse_mode=types.ParseMode.MARKDOWN)
mysql_connect.conf = db_conf[sys.argv[1:][0]]
user_stat.conf = db_conf[sys.argv[1:][0]]

mem_storage = MemoryStorage()
dp = Dispatcher(bot, storage=mem_storage)
posts_cb = CallbackData('post', 'data', 'action')


def load_data(name):
    data_file = Path(name)
    if data_file.is_file():
        with open(name, 'rb') as f:
            data_new = pickle.load(f)
    else:
        data_new = dict()
    return data_new


# print(user_language)
word_etimology = dict()

sessions = load_data("sessions.pkl")  # user_id: session
# tmp_voc = dict() #(user, language): (word, [definitions])

help_text = 'Welcome!\n' \
            '1. Select language to learn with /setlanguage.\n'\
            '  The bot will try to show word definitions in your user language set in Telegram if possible.\n' \
            '  You can change your user language with /settings command\n'\
            '2. Then /addwords to get exercises.\n' \
            '  Or you can add many words with /wordlist command.\n' \
            '3. Then type /learn to start training.\n' \
            '  - If you already learned some words, type /test\n' \
            '  - You can delete words with a /delete command\n\n' \
            'To see the words that you already added:\n' \
            ' /show - shows all added words in alphabetical order\n' \
            ' /show _date_ - shows all added words starting from oldest to newly added\n' \
            ' /show _abc_ - shows all words that start with _abc_ \n' \
            ' /show _last N_ - shows last N added words (replace _N_ with an actual number)\n\n' \
            'To get help:\n' \
            '- Type /help if you want to see this text again\n' \
            '- Start typing "/" any time to access the commands from the list'


# Test independent loop
@dp.message_handler(commands=['notify'])
async def send_notifications_to_users(message: types.Message):
    user_id = message.from_user.id
    if user_id != admin:
        logger.error("Wrong admin: " + str(user_id))
        await bot.send_message(admin, "Wrong admin: " + str(user_id))
        return
    notifications = user_stat.get_user_message(24)
    logger.warning(
        "sending {} notifications to users".format(len(notifications)))
    await bot.send_message(admin, "sending {} notifications to users".format(len(notifications)))
    blocked = 0
    for user_id, notification_text in notifications.items():
        time.sleep(.5)
        # user_id = admin #USE FOR TESTING
        try:
            logger.debug("Sending notification to " + str(user_id))
            await bot.send_message(user_id, notification_text, parse_mode=types.ParseMode.HTML)
        except Blocked as e:
            print(e)
            logger.warning("User {} blocked the bot".format(user_id))
            blocked += 1
            mysql_connect.update_blocked(user_id)
        except Exception as e:
            logger.error("Error sending notification: " + str(e))
    await bot.send_message(admin, str(blocked) + " users blocked the bot")


# Utils
async def get_session(user_id):
    if user_id in sessions.keys():
        return sessions[user_id]
    else:
        await bot.send_message(user_id, "You should /start the bot before learning")
        return None


async def authorize(user_id, with_lang=False):
    session = await get_session(user_id)
    if session is None:
        return session, False

    if (with_lang) and (session.active_lang() is None):
        await bot.send_message(user_id, "You need to /setlanguage first")
        return session, False
    return session, True


@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
    if sys.argv[1:][0] == 'dev':
        await bot.send_message(message.from_user.id,
                               "*A T T E N T I O N !*\nThis is a testing bot. Do not use it for learning words!")
    logger.info(str(message.from_user.id) + ' /start command')
    s = Session(message.from_user.id, message.from_user.first_name, message.from_user.last_name,
                message.from_user.language_code)
    if message.from_user.language_code is None:
        await bot.send_message(message.from_user.id, "Your user language is not set. It means that all word definitions will be in English. Set your Telegram user language and /start the bot again.")
    mysql_connect.update_user(message.from_user.id, message.from_user.first_name, message.from_user.last_name,
                              message.from_user.language_code)
    sessions[message.from_user.id] = s
    await message.reply(help_text)
    await bot.send_photo(message.from_user.id, types.InputFile('menu1.1.png'))


@dp.message_handler(commands=['help'])
async def help_message(message: types.Message):
    logger.info(str(message.from_user.id) + ' /help command')
    await message.reply(help_text)
    await bot.send_photo(message.from_user.id, types.InputFile('menu1.1.png'))
    await bot.send_message(message.from_user.id, "*If you have questions, you can ask them at https://t.me/OppiWords*")


@dp.message_handler(commands=['settings'])
async def help_message(message: types.Message):
    logger.info(str(message.from_user.id) + ' /settings command')
    session, isValid = await authorize(message.from_user.id, with_lang=True)
    if not isValid:
        return
    await bot.send_message(message.from_user.id, "A few settings to make.")
    await bot.send_message(message.from_user.id, "*If you have questions, you can ask them at https://t.me/OppiWords*")
    m = await bot.send_message(message.from_user.id, "Please, specify the language in which you want to get definitions (e.g. Russian or German or any other language name) "
                                                 "of words and phrases", reply_markup=types.ForceReply())
    session.status = m.message_id + 1


@dp.message_handler(lambda message: user_state(message.from_user.id, message.message_id))
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

# SHOW WORDS ========================================================
@dp.message_handler(commands=['show'])
async def start_message(message: types.Message):
    logger.info(str(message.from_user.id) + ' ' + str(message.text))

    session, isValid = await authorize(message.from_user.id, with_lang=True)
    if not isValid:
        return

    cmd = message.text
    if ' ' in cmd:
        cmd2 = str(cmd).split(' ')
        if cmd2[1] == 'list':
            #TODO ask for list name and show words from the list
            pass
        elif cmd2[1] == 'date':
            words = mysql_connect.fetchall("SELECT w.word, w.definition, DATE_FORMAT(s.created_at, '%Y-%m-%d') AS date FROM words w INNER JOIN spaced_repetition s ON w.hid = s.hid WHERE w.user =%s AND w.language=%s AND w.mode = 0 ORDER BY date",
                                           (session.get_user_id(), session.active_lang()))
        elif cmd2[1] == 'last':
            LIMIT = ""
            if len(cmd2) == 3:
                n = cmd2[2]
                LIMIT = ' LIMIT ' + str(n)

            words = mysql_connect.fetchall("SELECT w.word, w.definition, DATE_FORMAT(s.created_at, '%Y-%m-%d') AS date FROM words w INNER JOIN spaced_repetition s ON w.hid = s.hid WHERE w.user =%s AND w.language=%s AND w.mode = 0 ORDER BY date DESC" + LIMIT,
                                           (session.get_user_id(), session.active_lang()))
        else:
            letter = str(cmd2[1]) + '%'
            words = mysql_connect.fetchall(
                "SELECT word, definition FROM words WHERE user =%s AND language=%s AND mode = 0 AND word LIKE %s ORDER BY word",
                (session.get_user_id(), session.active_lang(), letter))

    else:
        words = mysql_connect.fetchall("SELECT word, definition FROM words WHERE user=%s AND language=%s AND mode = 0 ORDER BY word",
                                       (session.get_user_id(), session.active_lang()))

    for w in words:
        date_str = ""
        if len(w) == 3:
            date_str = "\n" + str(w[2])
        await bot.send_message(session.get_user_id(), "<b>{}</b> : {}".format(w[0], w[1]) + date_str,
                               parse_mode=types.ParseMode.HTML, disable_notification=True)
        time.sleep(.1)
    await bot.send_message(session.get_user_id(), "Total: {} words".format(len(words)))


# ADDING TEXT========================================================
@dp.message_handler(commands=['addtext'])
async def start_message(message: types.Message):
    user_id = message.from_user.id
    logger.info(str(user_id) + ' /addtext')

    session, isValid = await authorize(user_id, with_lang=True)
    if not isValid:
        return
    m = await bot.send_message(user_id, "Paste in a short text here.")
    session.status = m.message_id + 1


@dp.message_handler(lambda message: user_state(message.from_user.id, message.message_id))
async def start_message(message: types.Message):
    user_id = message.from_user.id
    logger.info(str(user_id) + ' /addtext received')
    session = await get_session(user_id)
    if session is None:
        return
    text_words = set(word_lists.tokenize_text(
        message.text, session.active_lang()))
    list_name = message.text[:30]
    await bot.send_message(session.get_user_id(), (
        "The list name is _{}_.The words are ready to be added to your dictionary. /addwords to do so.".format(
            list_name)))
    mysql_connect.add_list(user=str(
        session.get_user_id()), word_list=text_words, lang=session.active_lang(), list_name=list_name)
    session.status = None
    await adding_list_words(message, None, list_name)


# ADDING LIST ======================================================
@dp.message_handler(commands=['wordlist'])
async def start_message(message: types.Message):
    user_id = message.from_user.id
    logger.info(str(user_id) + ' /wordlist')
    session, isValid = await authorize(user_id, with_lang=True)
    if not isValid:
        return
    tokens = ["Top frequency words", "Smart list (coming soon)"]
    data = [0, 0]
    actions = ['topn', 'smart']
    k = to_vertical_keyboard(tokens=tokens, data=data, action=actions)
    await bot.send_message(session.get_user_id(), "What type of lists would you like?", reply_markup=k)


@dp.callback_query_handler(posts_cb.filter(action=["topn"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    session, isValid = await authorize(query.from_user.id, with_lang=True)
    if not isValid:
        return
    lang = session.active_lang().title()
    session.status = 'topn'
    m = query.message
    await m.edit_reply_markup()
    # await m.edit_text("How many words would you like? (only digits: 10 or 50 or any other value)"
    await m.edit_text("Type _0:100_ if you want to add top 100 most frequent words for {}"
                      "\nor _50:100_ if you want to skip top 50 words. You can specify any range in the format _start:end_"
                      "\nThe words don't have definitions. You will add them afterwards. ".format(lang))


@dp.message_handler(lambda message: user_state(message.from_user.id, "topn"))
async def adding_word_to_list(message):
    session, isValid = await authorize(message.from_user.id, with_lang=True)
    if not isValid:
        return
    session.status = 'topn'
    n = message.text
    if not re.match("\d+:\d+", n):
        await bot.send_message(session.get_user_id(), "Please use format: _start:end_. "
                               "For example _0:50_ to get top 50 most frequent words")
        return
    start = int(str(n).split(':')[0])
    end = int(str(n).split(':')[1])
    if start >= end:
        await bot.send_message(session.get_user_id(), "Please use format: _start:end_. "
                               "For example _0:50_ to get top 50 most frequent words")
        return
    topn = word_lists.get_top_n(
        lang=session.active_lang(), start=start, end=end)
    list_name = str(session.active_lang()) + " top" + str(n)
    if topn is None:
        logger.error("{} is adding list {}, which is None".format(
            session.get_user_id(), list_name))
        await bot.send_message(session.get_user_id(), "Sorry cannot add your list. Try again")
        return
    logger.debug("{} is adding list {}, list length {}".format(
        session.get_user_id(), list_name, len(topn)))
    await bot.send_message(session.get_user_id(), (
        "The list name is {}.The words are ready to be added to your dictionary. /addwords to do so.".format(
            list_name)))
    mysql_connect.add_list(user=str(session.get_user_id()), word_list=topn,
                           lang=session.active_lang(), list_name=list_name)
    session.status = None
    await adding_list_words(message, None, list_name)


async def adding_list_words(message, query, list_name):
    if query is None:
        session, isValid = await authorize(message.from_user.id, with_lang=True)
    elif message is None:
        session, isValid = await authorize(query.from_user.id, with_lang=True)
    if not isValid:
        return
    if session.list_hid_word is not None:
        hid = session.list_hid_word[1]
        list_name = session.list_hid_word[0]
        mysql_connect.delete_from_list(hid)
    session.status = '/addwords'
    word_list = mysql_connect.get_list(
        session.get_user_id(), session.active_lang(), list_name)
    if len(word_list) == 0 and list_name is not None:
        await bot.send_message(session.get_user_id(), "You added all words from the list *{}*\n"
                               "Now you can /learn words".format(list_name.title()))
        return
    if list_name is None:
        logger.error("{}, list_name is None".format(session.get_user_id()))
        return

    word = word_list[0][2]
    m = await bot.send_message(session.get_user_id(), "{} words to add from list _{}_\n*{}*".format(len(word_list), list_name.title(), word))
    session.list_hid_word = word_list[0]
    m.text = word
    m.from_user.id = session.get_user_id()
    await wiktionary_search(m)


@dp.callback_query_handler(posts_cb.filter(action=["next_word_from_list"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    await query.message.edit_reply_markup()
    await query.message.edit_text("Next word")
    await adding_list_words(None, query, None)


# DELETING =======================================================

@dp.message_handler(commands=['delete'])
async def delete_message(message: types.Message):
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    logger.info(str(session.get_user_id()) + ' /delete command')
    session.status = "delete"
    await message.reply('Write the word you want to delete')


@dp.message_handler(lambda message: user_state(message.from_user.id, "delete"))
async def deleting_word(message):
    session, isValid = await authorize(message.from_user.id, with_lang=True)
    if not isValid:
        return
    logger.info(str(session.get_user_id())
                + " is deleting word " + message.text)
    data = mysql_connect.fetchone("SELECT word, definition, hid FROM words "
                                  "WHERE user=%s and language=%s and word=%s",
                                  (session.get_user_id(), session.active_lang(), message.text))
    session.status = ""
    if data is None:
        await bot.send_message(session.get_user_id(), 'The words does not exist in you dictionary')
        return
    session.hid_cash = data[2]
    k = to_one_row_keyboard(["Keep", "Delete"], data=[
                            0, 1], action=["keep", "delete"])
    await bot.send_message(session.get_user_id(), "Do you want to delete word *{}* with definition\n{}"
                           .format(data[0], data[1]), reply_markup=k)


@dp.callback_query_handler(posts_cb.filter(action=["delete"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    await query.answer()
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    logger.info(str(session.get_user_id())
                + ' is deleting word ' + session.hid_cash)
    result = mysql_connect.delete_by_hid(session.hid_cash)
    session.hid_cash = ""
    if result:
        await bot.send_message(session.get_user_id(), 'The word is deleted')
    else:
        logger.warn(str(session.get_user_id())
                    + ' failed to delete word ' + session.hid_cash)
        await bot.send_message(session.get_user_id(), 'Failed to delete the words')


@dp.callback_query_handler(posts_cb.filter(action=["keep"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    await query.answer()
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    logger.info(str(session.get_user_id()) + ' is keeping word ' + session.hid_cash)
    session.hid_cash = ""
    await bot.send_message(session.get_user_id(), "OK, let's keep it")


# ==========================================================================================
# Learning

# Checking prerequisites and collecting data
@dp.message_handler(commands=['learn', 'test'])
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


@dp.callback_query_handler(posts_cb.filter(action=["start_learning"]))
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
        await do_reading_errors(query, callback_data)
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
    random.shuffle(words)
    session.words_to_learn = words
    await bot.send_message(session.get_user_id(), "Check if you remember these words")
    await do_learning(session)


# Reading errors loop, end of the learning loop if no more words to learn
@dp.callback_query_handler(posts_cb.filter(action=["mc_correct", "reading_errors"]))
async def do_reading_errors(query: types.CallbackQuery, callback_data: dict):
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    if "mc_correct" == callback_data['action']:
        session.delete_current_error()
        n = len(session.read_error_storage)
        if n > 0:
            await query.answer("Yes! " + str(n) + " to go")
        elif n == 0:
            await query.answer("Yes! And that is all.")
    await do_reading_errors1(session)


async def do_reading_errors1(session):
    bot_response = ["What word matches this definition?",
                    "What word is correct for this definition?"]
    if session.has_more_errors():
        word, variants = session.get_next_error()
        variants = list.copy(variants)
        variants.append(word[0])
        random.shuffle(variants)
        c = variants.index(word[0])
        a = ["mc_wrong"] * len(variants)
        a[c] = "mc_correct"
        definition = word[1]
        keyboard = to_vertical_keyboard(variants,
                                        data=[-3] * len(variants),
                                        action=a)  # mc = multiple choice
        if word[2] < 2:
            await bot.send_message(session.get_user_id(), bot_response[word[2]])

        try:
            await bot.send_message(session.get_user_id(), definition, reply_markup=keyboard)
        except CantParseEntities as e:
            logger.warning(e)
            string = session.get_current_definition()
            string = str(string).replace('*', '')
            string = str(string).replace('_', '')
            string = str(string).replace('`', '')
            await bot.send_message(session.get_user_id(), string, reply_markup=keyboard)
    else:
        if session.has_more_words_to_learn():
            await do_learning1(session.get_user_id())
        else:
            await bot.send_message(session.get_user_id(),
                                   "Congrats! You've learned all the words for now)\nYou may want to /test the words you've learned")
            session.user_status = None


# The learning loop, reading task 1
@dp.callback_query_handler(posts_cb.filter(action=["do_learning"]))
async def do_learning(session):
    session, isValid = await authorize(session.get_user_id())
    if not isValid:
        return
    await do_learning1(session)


async def do_learning1(session):
    if not session.has_more_words_to_learn():
        await do_reading_errors1(session)
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
        elif word[2] == 1:
            session.status = "type_in"
            await bot.send_message(session.get_user_id(), "Write the correct word for the definition:\n*" + word[1] + "*")


@dp.message_handler(lambda message: user_state(message.from_user.id, 'type_in'))
async def type_in_message(message):
    logger.info(str(message.from_user.id) + " Type_in message")
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    word = session.get_current_word()
    if word is None:
        await bot.send_message(session.get_user_id(), RESTART)
        logger.error(str(session.get_user_id()) + " word is None (2)")
        return
    word = word[0]
    if str(word).lower() == str(message.text).lower():
        sr.update_item(session.get_current_hid(), 1)
        session.delete_current_word()
        n = len(session.words_to_learn) - session.current_word
        if n > 0:
            await bot.send_message(session.get_user_id(), "*Correct!* *{}* to go".format(n))
        time.sleep(2)
    else:
        sr.update_item(session.get_current_hid(), 0)
        await bot.send_message(session.get_user_id(), "Wrong. It is *" + session.get_current_word()[0] + "*")
        time.sleep(3)
        misspelt_word = str(message.text)
        if word[0].isupper():
            misspelt_word = misspelt_word.capitalize()
        else:
            misspelt_word = misspelt_word.lower()
        session.add_writing_error(misspelt_word)
    session.status = None
    await do_learning1(session)


# reading task 1 answer "I remember"
@dp.callback_query_handler(posts_cb.filter(action=["I_remember"]))
async def i_remember(query: types.CallbackQuery, callback_data: dict):
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    hid = session.get_current_hid()
    sr.update_item(hid, 1)
    new_hid = sr.add_item((session.get_user_id(), session.active_lang()),
                          (session.get_current_word()[0],
                           session.get_current_definition()),
                          session.get_current_mode() + 1)

    mysql_connect.insert_word(session.get_user_id(), session.active_lang(),
                              session.get_current_word()[0],
                              session.get_current_definition(),
                              session.get_current_mode() + 1, new_hid)
    session.level_up_current_word(new_hid)
    session.delete_current_word()
    n = len(session.words_to_learn) - session.current_word
    if n > 0:
        await query.answer(str(n) + " to go")
    await do_learning(session)


# reading task showing definition, adding word to the error list
@dp.callback_query_handler(posts_cb.filter(action="show"))
async def callback_show_action(query: types.CallbackQuery, callback_data: dict):
    logger.info('Got this callback data: %r', callback_data)
    await query.answer()
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    session.add_error()
    kb = to_one_row_keyboard(["Yes, I knew that!", "No, I forgot it"],
                             data=[0.5, 0],
                             action=["i_knew", "forgot"])
    try:
        await bot.send_message(query.from_user.id, session.get_current_definition(), reply_markup=kb)
    except CantParseEntities as e:
        logger.warning(e)
        string = session.get_current_definition()
        string = str(string).replace('*', '')
        string = str(string).replace('_', '')
        string = str(string).replace('`', '')
        await bot.send_message(query.from_user.id, string, reply_markup=kb)


# Forgot and I knew that!
@dp.callback_query_handler(posts_cb.filter(action=["forgot", "i_knew"]))
async def callback_forgot_action(query: types.CallbackQuery, callback_data: dict):
    logger.debug(str(query.from_user.id)
                 + ' Got this callback data: %r', callback_data)
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    hid = session.get_current_hid()
    if hid is None:
        logger.error(str(session.get_user_id()) + ' hid is None')
        await bot.send_message(session.get_user_id(), RESTART)
        return
    sr.update_item(hid, float(callback_data['data']))
    session.delete_current_word()
    n = len(session.words_to_learn) - session.current_word
    if n > 0:
        await query.answer(str(n) + " words to go")
    await do_learning(session)


@dp.callback_query_handler(posts_cb.filter(action=["mc_wrong"]))
async def callback_mc_action(query: types.CallbackQuery, callback_data: dict):
    logger.debug('Got this callback data: %r', callback_data)
    await query.answer("Wrong.")
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    answer = session.get_error_answer()
    session.move_error_down()
    k = to_one_row_keyboard(["OK"], data=[1], action=["reading_errors"])
    await bot.send_message(chat_id=session.get_user_id(), text="It's " + answer, reply_markup=k)
    # await do_reading_errors(query, callback_data)


# ==========================================================================================
# Selecting a language to learn

@dp.message_handler(commands=['setlanguage'])
async def setlanguage_command_message(message: types.Message):
    logger.debug(message)
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    session.status = 'setlanguage'
    if " " in message.text or message.text != '/setlanguage':
        await setlanguage_message(message)
    else:

        forced_reply = types.ForceReply()
        await message.reply("Type the name of the language to learn (e.g. English, Finnish or other.\n"
                            "You can always change it with /setlanguage", reply_markup=forced_reply)


@dp.callback_query_handler(posts_cb.filter(action=["setlanguage"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    session.status = "setlanguage"
    await setlanguage_message(query.message.reply_to_message)


@dp.message_handler(lambda message: user_state(message.from_user.id, "setlanguage"))
async def setlanguage_message(message):
    logger.debug("Received message")
    logger.debug(message)
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    language_name = str(message.text)
    if language_name == "":
        await message.reply("OK, let's skip it for now")
    elif language_name.startswith("/setlanguage") and " " in language_name:
        language_name = language_name.split(" ", 1)[1]
    if " " in language_name:
        await message.reply("Language name is wrong. It must be one word only (e.g. _English_)")
    else:
        if language_name[0] == '/':
            logger.warning(str(message.from_user.id)
                           + " set language " + language_name)
            language_name = language_name[1:]
        if language_name.lower() not in LANGS:
            await message.reply("Sorry, can't recognize the language name. Make sure it's correct and is *in English* "
                                "(e.g. instead of _Deutsch_ use _German_).")
            return
        await message.reply("Language is set to *" + language_name.title() + "*")
        await bot.send_message(message.from_user.id, "Now you can /addwords to /learn")
        logger.info(str(message.chat.id) + " learns " + language_name)
        session.set_active_language(language_name.lower())
        logger.debug(session.active_lang())
        with open('sessions.pkl', 'wb') as f:
            pickle.dump(sessions, f)
        session.status = None


# ==========================================================================================
# Adding new words

# Getting the command, setting s.status ="/addwords"
@dp.message_handler(commands=['addwords'])
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


def user_state(user_id, state):
    if user_id not in sessions.keys():
        return False
    return sessions[user_id].status == state


@dp.callback_query_handler(posts_cb.filter(action=["skip_list"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    session.status = "/addwords"
    session.words_to_add = None
    session.list_hid_word = None
    logger.debug(str(query.from_user.id) + session.status)
    await bot.send_message(query.from_user.id, "Type in words in *" + session.active_lang().title() + "*")

# Getting a new word typed in by a user and getting definitions
@dp.callback_query_handler(posts_cb.filter(action=["wiktionary_search"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    message = query.message.reply_to_message
    await wiktionary_search(message)


@dp.message_handler(lambda message: user_state(message.from_user.id, "/addwords"))
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
    data=list(range(0, len(actions), 1))

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
        await bot.send_message(session.get_user_id(), "Tap a button with a meaning to learn", reply_markup=k, parse_mode=types.ParseMode.MARKDOWN)
    else:
        await bot.edit_message_reply_markup(session.get_user_id(), query.message.message_id, reply_markup=k)


# Adding selected definition
@dp.callback_query_handler(posts_cb.filter(action=["meaning"]))
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


@dp.callback_query_handler(posts_cb.filter(action=["add_user_definition"]))
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
            await adding_list_words(None, query, None)
    else:
        session.status = 'adding_user_definition'
        word = session.words_to_add[0]
        await bot.send_message(query.message.chat.id,
                               "Type in your definition for {}".format(word),
                               reply_markup=types.ForceReply())


@dp.message_handler(lambda message: user_state(message.from_user.id, "adding_user_definition"))
async def adding_words(message):
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    definition = message.text
    word = session.words_to_add[0]
    session.words_to_add = None
    logger.debug(word + ": " + definition)
    await add_word_to_storage(session=session,
                              word=word,
                              definition=definition)
    session.status = "/addwords"
    if session.list_hid_word is not None:
        await adding_list_words(message, None, None)
    else:
        await bot.send_message(message.from_user.id, "OK")


@dp.callback_query_handler(posts_cb.filter(action=["finish_adding_meanings"]))
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


# UNKNOWN input
# ===============================================================

@dp.callback_query_handler()
async def unknow_query_handler(query: types.CallbackQuery):
    logger.info('Got this callback data: %r', query.data)
    logger.info('Got this query.as_json: %r', query.as_json())
    await query.answer("Don't know what to do))")
    # callback_data_action = callback_data['action']
    # logger.info(callback_data_action)


@dp.message_handler()
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


if __name__ == '__main__':
    print(sys.argv[1:])
    with open('lang.list') as f:
        LANGS = f.readlines()
    LANGS = [x.replace('\n', '').lower() for x in LANGS]
    executor.start_polling(dp, skip_updates=True)
