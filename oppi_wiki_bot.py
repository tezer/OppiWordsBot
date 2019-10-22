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
# addwords - add words to learn
# setlanguage - specify a language you want to learn. You can switch between languages or add new ones any time
# learn - learn the words you added
# test - test the words you learned
# delete - delete a word form your dictionary
# wordlist - add a list of words (you will have to add definitions after adding the list)


bot = Bot(token=bot_token[sys.argv[1:][0]], parse_mode=types.ParseMode.MARKDOWN)
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

help_text = 'Welcome!' \
            '\nFirst, select language to learn with /setlanguage.' \
            '\nThen /addwords to get exercises. ' \
            '\nThen type /learn to start training.' \
            '\nIf you already learned some words, type /test' \
            '\nYou can delete words with a /delete command' \
            '\nType /help if you want to see this text again.' \
            '\nYou can always access the commands from the list which is in *the down right corner of the bot window*.'


# Test independent loop
@dp.message_handler(commands=['notify'])
async def send_notifications_to_users(message: types.Message):
    user_id = message.from_user.id
    if user_id != admin:
        logger.error("Wrong admin: " + str(user_id))
        await bot.send_message(admin, "Wrong admin: " + str(user_id))
        return
    notifications = user_stat.get_user_message(24)
    logger.warning("sending {} notifications to users".format(len(notifications)))
    await bot.send_message(admin, "sending {} notifications to users".format(len(notifications)))
    blocked = 0
    for user_id, notification_text in notifications.items():
        time.sleep(1)
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
        # s = session.Session(user_id)
        # sessions[user_id] = s
        return None


@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
    if sys.argv[1:][0] == 'dev':
        await bot.send_message(message.from_user.id,
                               "*A T T E N T I O N !*\nThis is a testing bot. Do not use it for learning words!")
    logger.info(str(message.from_user.id) + ' /start command')
    s = Session(message.from_user.id, message.from_user.first_name, message.from_user.last_name,
                message.from_user.language_code)
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

# ADDING TEXT========================================================
@dp.message_handler(commands=['addtext'])
async def start_message(message: types.Message):
    user_id = message.from_user.id
    logger.info(str(user_id) + ' /addtext')
    s = await get_session(user_id)
    if s is None:
        return
    if s.active_lang() is None:
        await bot.send_message(user_id, "You need to /setlanguage first")
        return
    m = await bot.send_message(user_id, "Paste in a short text here.")
    print(m.message_id)
    s.status = m.message_id + 1


@dp.message_handler(lambda message: user_state(message.from_user.id, message.message_id))
async def start_message(message: types.Message):
    user_id = message.from_user.id
    logger.info(str(user_id) + ' /addtext received')
    s = await get_session(user_id)
    if s is None:
        return
    text_words = set(word_lists.tokenize_text(message.text, s.active_lang()))
    list_name = message.text[:30]
    await bot.send_message(user_id, (
        "The list name is _{}_.The words are ready to be added to your dictionary. /addwords to do so.".format(
            list_name)))
    mysql_connect.add_list(user=str(user_id), word_list=text_words, lang=s.active_lang(), list_name=list_name)
    s.status = None
    await adding_list_words(message, None, list_name)


# ADDING LIST ======================================================
@dp.message_handler(commands=['wordlist'])
async def start_message(message: types.Message):
    user_id = message.from_user.id
    logger.info(str(user_id) + ' /wordlist')
    s = await get_session(user_id)
    if s is None:
        return
    if s.active_lang() is None:
        await bot.send_message(user_id, "You need to /setlanguage first")
        return

    tokens = ["Top frequency words", "Smart list (coming soon)"]
    data = [0, 0]
    actions = ['topn', 'smart']
    k = to_vertical_keyboard(tokens=tokens, data=data, action=actions)
    await bot.send_message(user_id, "What type of lists would you like?", reply_markup=k)


@dp.callback_query_handler(posts_cb.filter(action=["topn"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    user_id = query.from_user.id
    s = await get_session(user_id)
    lang = s.active_lang().title()
    if s is None:
        return
    s.status = 'topn'
    m = query.message
    await m.edit_reply_markup()
    # await m.edit_text("How many words would you like? (only digits: 10 or 50 or any other value)"
    await m.edit_text("Type _0:100_ if you want to add top 100 most frequent words for {}"
                      "\nor _50:100_ if you want to skip top 50 words. You can specify any range in the format _start:end_"
                      "\nThe words don't have definitions. You will add them afterwards. ".format(lang))


@dp.message_handler(lambda message: user_state(message.from_user.id, "topn"))
async def adding_word_to_list(message):
    user_id = message.from_user.id
    s = await get_session(user_id)
    if s is None:
        return
    s.status = 'topn'
    n = message.text
    if not re.match("\d+:\d+", n):
        await bot.send_message(user_id, "Please use format: _start:end_. "
                                        "For example _0:50_ to get top 50 most frequent words")
        return
    start = int(str(n).split(':')[0])
    end = int(str(n).split(':')[1])
    if start >= end:
        await bot.send_message(user_id, "Please use format: _start:end_. "
                                        "For example _0:50_ to get top 50 most frequent words")
        return
    topn = word_lists.get_top_n(lang=s.active_lang(), start=start, end=end)
    list_name = str(s.active_lang()) + " top" + str(n)
    logger.debug("{} is adding list {}, list length {}".format(user_id, list_name, len(topn)))
    if topn is None:
        logger.error("{} is adding list {}, which is None".format(user_id, list_name))
        await bot.send_message(user_id, "Sorry cannot add your list. Try again")
        return
    await bot.send_message(user_id, (
        "The list name is {}.The words are ready to be added to your dictionary. /addwords to do so.".format(
            list_name)))
    mysql_connect.add_list(user=str(user_id), word_list=topn, lang=s.active_lang(), list_name=list_name)
    s.status = None
    await adding_list_words(message, None, list_name)


async def adding_list_words(message, query, list_name):
    if message is None:
        user_id = query.from_user.id
    else:
        user_id = message.from_user.id
    s = await get_session(user_id)
    if s is None:
        return

    if s.list_hid_word is not None:
        hid = s.list_hid_word[1]
        list_name = s.list_hid_word[0]
        mysql_connect.delete_from_list(hid)
    s.status = '/addwords'
    word_list = mysql_connect.get_list(user_id, s.active_lang(), list_name)
    if len(word_list) == 0:
        await bot.send_message(user_id, "You added all words from the list *{}*\n"
                                        "Now you can /learn words".format(list_name.title()))
        return
    word = word_list[0][2]
    m = await bot.send_message(user_id, "{} words to add from list _{}_\n*{}*".format(len(word_list), list_name.title(), word))
    s.list_hid_word = word_list[0]
    m.text = word
    m.from_user.id = user_id
    await wiktionary_search(m)

@dp.callback_query_handler(posts_cb.filter(action=["next_word_from_list"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    await query.message.edit_reply_markup()
    await query.message.edit_text("Next word")
    await adding_list_words(None, query, None)




# DELETING =======================================================

@dp.message_handler(commands=['delete'])
async def delete_message(message: types.Message):
    user_id = message.from_user.id
    s = await get_session(user_id)
    if s is None:
        return
    logger.info(str(user_id) + ' /delete command')
    s.status = "delete"
    await message.reply('Write the word you want to delete')


@dp.message_handler(lambda message: user_state(message.from_user.id, "delete"))
async def deleting_word(message):
    user_id = message.from_user.id
    s = await get_session(user_id)
    if s is None:
        return
    logger.info(str(user_id) + " is deleting word " + message.text)
    data = mysql_connect.fetchone("SELECT word, definition, hid FROM words "
                                  "WHERE user=%s and language=%s and word=%s",
                                  (user_id, s.active_lang(), message.text))
    s.status = ""
    if data is None:
        await bot.send_message(user_id, 'The words does not exist in you dictionary')
        return
    s.hid_cash = data[2]
    k = to_one_row_keyboard(["Keep", "Delete"], data=[0, 1], action=["keep", "delete"])
    await bot.send_message(user_id, "Do you want to delete word *{}* with definition\n{}"
                           .format(data[0], data[1]), reply_markup=k)


@dp.callback_query_handler(posts_cb.filter(action=["delete"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    user_id = query.from_user.id
    await query.answer()
    s = await get_session(user_id)
    if s is None:
        return
    logger.info(str(user_id) + ' is deleting word ' + s.hid_cash)
    result = mysql_connect.delete_by_hid(s.hid_cash)
    s.hid_cash = ""
    if result:
        await bot.send_message(user_id, 'The word is deleted')
    else:
        logger.warn(str(user_id) + ' failed to delete word ' + s.hid_cash)
        await bot.send_message(user_id, 'Failed to delete the words')


@dp.callback_query_handler(posts_cb.filter(action=["keep"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    user_id = query.from_user.id
    await query.answer()
    s = await get_session(user_id)
    if s is None:
        return
    logger.info(str(user_id) + ' is keeping word ' + s.hid_cash)
    s.hid_cash = ""
    await bot.send_message(user_id, "OK, let's keep it")


# ==========================================================================================
# Learning

# Checking prerequisites and collecting data
@dp.message_handler(commands=['learn', 'test'])
async def start_learning_message(message):
    user_id = message.from_user.id
    s = await get_session(user_id)
    if s is None:
        return
    if len(s.languages) == 0:
        await message.reply("You need set the language you learn with /setlanguage command")
        return True
    if message.text == '/test':
        s.status = '/test'  # FIXME do I need it? (Used in adding words to specify calls. Should be replaced with normal dp.callback_query_handler
    if message.text == '/learn':
        s.status = '/learn'
    await message.reply("OK, let's learn some " + s.active_lang())
    kb = to_one_row_keyboard(["10", "20", "30", "40", "All"],
                             data=[10, 20, 30, 40, 1000],
                             action=["start_learning"] * 5)
    await bot.send_message(user_id, "How many words should I offer to you this time?",
                           reply_markup=kb)


@dp.callback_query_handler(posts_cb.filter(action=["start_learning"]))
async def learning(query: types.CallbackQuery, callback_data: dict):
    await query.answer("Let's learn!")
    logger.debug(query)
    logger.debug(str(query.from_user.id) + "start_learning  " + str(callback_data))
    n = int(callback_data['data'])
    user_id = query.from_user.id
    s = await get_session(user_id)
    if s is None:
        return

    if n > 0:  # 10, 20, 30, 40, 1000
        hids = list()
        if s.status == '/test':
            hids = sr.get_items_to_learn((user_id, s.active_lang()), upper_recall_limit=1.0, n=n)
        if s.status == '/learn':
            hids = sr.get_items_to_learn((user_id, s.active_lang()), upper_recall_limit=0.5, n=n)
        if len(hids) == 0:
            if s.status == '/test':
                await bot.send_message(user_id,
                                       'You should add at least one word with /addwords command to start training')
            else:
                await bot.send_message(user_id, 'You don\'t have words for training.')
                await bot.send_message(user_id, 'Add more words with /addwords command or')
                await bot.send_message(user_id, 'or /test words you learned before.')
            return True
    words = mysql_connect.fetch_by_hids(user_id, hids)
    s.words_to_learn = words
    s.current_word = 0

    if not s.has_more_words_to_learn():
        # Case 2: doing reading errors
        await bot.send_message(user_id, "Let's revise some words")
        await do_reading_errors(query, callback_data)
    else:
        # Case 1: reading exercises
        await start_learning(query, callback_data)


# Get reply from the user and filter the data: set number and shuffle
async def start_learning(query: types.CallbackQuery, callback_data: dict):
    user_id = query.from_user.id
    n = int(callback_data['data'])
    s = await get_session(user_id)
    if s is None:
        return
    words = s.words_to_learn
    if n > len(words):
        await bot.send_message(user_id, "You have only *" + str(len(words)) + "* words for this session")
    if n < len(words):
        words = words[:n]
    random.shuffle(words)
    s.words_to_learn = words
    await bot.send_message(user_id, "Check if you remember these words")
    await do_learning(query, callback_data)


# Reading errors loop, end of the learning loop if no more words to learn
@dp.callback_query_handler(posts_cb.filter(action=["mc_correct", "reading_errors"]))
async def do_reading_errors(query: types.CallbackQuery, callback_data: dict):
    user_id = query.from_user.id
    s = await get_session(user_id)
    if s is None:
        return
    if "mc_correct" == callback_data['action']:
        s.delete_current_error()
        n = len(s.read_error_storage)
        if n > 0:
            await query.answer("Yes! " + str(n) + " to go")
    await do_reading_errors1(user_id)


async def do_reading_errors1(user_id):
    s = await get_session(user_id)
    if s is None:
        return
    if s.has_more_errors():
        word, variants = s.get_next_error()
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
        if word[3] == 0:
            await bot.send_message(user_id, "What word matches this definition?")
        if word[3] == 1:
            await bot.send_message(user_id, "What word is correct for this definition?")
        try:
            await bot.send_message(user_id, definition, reply_markup=keyboard)
        except CantParseEntities as e:
            logger.warning(e)
            string = s.get_current_definition()
            string = str(string).replace('*', '')
            string = str(string).replace('_', '')
            string = str(string).replace('`', '')
            await bot.send_message(user_id, string, reply_markup=keyboard)
    else:
        if s.has_more_words_to_learn():
            await do_learning1(user_id)
        else:
            await bot.send_message(user_id,
                                   "Congrats! You've learned all the words for now)\nYou may want to /test the words you've learned")
            s.user_status = None


# The learning loop, reading task 1
@dp.callback_query_handler(posts_cb.filter(action=["do_learning"]))
async def do_learning(query: types.CallbackQuery, callback_data: dict):
    user_id = query.from_user.id
    await do_learning1(user_id)


async def do_learning1(user_id):
    s = await get_session(user_id)
    if s is None:
        return
    if not s.has_more_words_to_learn():
        await do_reading_errors1(user_id)
    else:
        s = await get_session(user_id)
        if s is None:
            return
        word = s.get_current_word()  # 0. word, 1. definition, 2. mode, 3. hid
        if word is None:
            await bot.send_message(user_id, RESTART)
            logger.error(str(user_id) + " word is None")
            return
        if word[2] == 0:
            # Do reading exercises
            keyboard = to_one_row_keyboard(["I remember", "Show meaning"],
                                           data=[0, 1],
                                           action=["I_remember", "show"])
            hint = get_hint(word[1])
            await bot.send_message(user_id, '*' + word[0] + "*\n" + hint, reply_markup=keyboard)
        elif word[2] == 1:
            s.status = "type_in"
            await bot.send_message(user_id, "Write the correct word for the definition:\n*" + word[1] + "*")


@dp.message_handler(lambda message: user_state(message.from_user.id, 'type_in'))
async def type_in_message(message):
    user_id = message.from_user.id
    logger.info(str(user_id) + " Type_in message")
    s = await get_session(user_id)
    if s is None:
        return
    word = s.get_current_word()
    if word is None:
        await bot.send_message(user_id, RESTART)
        logger.error(str(user_id) + " word is None (2)")
        return
    word = word[0]
    if str(word).lower() == str(message.text).lower():
        sr.update_item(s.get_current_hid(), 1)
        s.delete_current_word()
        n = len(s.words_to_learn) - s.current_word
        if n > 0:
            await bot.send_message(user_id, "*Correct!* *{}* to go".format(n))
        time.sleep(2)
    else:
        sr.update_item(s.get_current_hid(), 0)
        await bot.send_message(user_id, "Wrong. It is *" + s.get_current_word()[0] + "*")
        time.sleep(3)
        misspelt_word = str(message.text)
        if word[0].isupper():
            misspelt_word = misspelt_word.capitalize()
        else:
            misspelt_word = misspelt_word.lower()
        s.add_writing_error(misspelt_word)
    s.status = None
    await do_learning1(user_id)


# reading task 1 answer "I remember"
@dp.callback_query_handler(posts_cb.filter(action=["I_remember"]))
async def i_remember(query: types.CallbackQuery, callback_data: dict):
    user_id = query.from_user.id
    s = await get_session(user_id)
    if s is None:
        return
    hid = s.get_current_hid()
    sr.update_item(hid, 1)
    new_hid = sr.add_item((user_id, s.active_lang()),
                          (s.get_current_word()[0], s.get_current_definition()),
                          s.get_current_mode() + 1)

    mysql_connect.insert_word(user_id, s.active_lang(),
                              s.get_current_word()[0],
                              s.get_current_definition(),
                              s.get_current_mode() + 1, new_hid)
    s.level_up_current_word(new_hid)
    s.delete_current_word()
    n = len(s.words_to_learn) - s.current_word
    if n > 0:
        await query.answer(str(n) + " to go")
    await do_learning(query, callback_data)


# reading task showing definition, adding word to the error list
@dp.callback_query_handler(posts_cb.filter(action="show"))
async def callback_show_action(query: types.CallbackQuery, callback_data: dict):
    logger.info('Got this callback data: %r', callback_data)
    await query.answer()
    s = await get_session(query.from_user.id)
    if s is None:
        return
    s.add_error()
    kb = to_one_row_keyboard(["Yes, I knew that!", "No, I forgot it"],
                             data=[0.5, 0],
                             action=["i_knew", "forgot"])
    try:
        await bot.send_message(query.from_user.id, s.get_current_definition(), reply_markup=kb)
    except CantParseEntities as e:
        logger.warning(e)
        string = s.get_current_definition()
        string = str(string).replace('*', '')
        string = str(string).replace('_', '')
        string = str(string).replace('`', '')
        await bot.send_message(query.from_user.id, string, reply_markup=kb)


# Forgot and I knew that!
@dp.callback_query_handler(posts_cb.filter(action=["forgot", "i_knew"]))
async def callback_forgot_action(query: types.CallbackQuery, callback_data: dict):
    user_id = query.from_user.id
    logger.debug(str(user_id) + ' Got this callback data: %r', callback_data)
    s = await get_session(user_id)
    if s is None:
        return
    hid = s.get_current_hid()
    if hid is None:
        logger.error(str(user_id) + ' hid is None')
        bot.send_message(user_id, RESTART)
        return
    sr.update_item(hid, float(callback_data['data']))
    s.delete_current_word()
    n = len(s.words_to_learn) - s.current_word
    if n > 0:
        await query.answer(str(n) + " words to go")
    await do_learning(query, callback_data)


@dp.callback_query_handler(posts_cb.filter(action=["mc_wrong"]))
async def callback_mc_action(query: types.CallbackQuery, callback_data: dict):
    logger.debug('Got this callback data: %r', callback_data)
    await query.answer("Wrong.")
    user_id = query.from_user.id
    s = await get_session(user_id)
    if s is None:
        return
    answer = s.get_error_answer()
    s.move_error_down()
    k = to_one_row_keyboard(["OK"], data=[1], action=["reading_errors"])
    await bot.send_message(chat_id=user_id, text="It's " + answer, reply_markup=k)
    # await do_reading_errors(query, callback_data)


# ==========================================================================================
# Selecting a language to learn

@dp.message_handler(commands=['setlanguage'])
async def setlanguage_command_message(message: types.Message):
    logger.debug(message)
    s = await get_session(message.from_user.id)
    if s is None:
        return
    s.status = 'setlanguage'
    if " " in message.text or message.text != '/setlanguage':
        await setlanguage_message(message)
    else:

        forced_reply = types.ForceReply()
        await message.reply("Set language to learn (e.g. English, Finnish or other.\n"
                            "You can always change it with /setlanguage", reply_markup=forced_reply)


@dp.callback_query_handler(posts_cb.filter(action=["setlanguage"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    s = await get_session(query.from_user.id)
    if s is None:
        return
    s.status = "setlanguage"
    await setlanguage_message(query.message.reply_to_message)


@dp.message_handler(lambda message: user_state(message.from_user.id, "setlanguage"))
async def setlanguage_message(message):
    logger.debug("Received message")
    logger.debug(message)
    s = await get_session(message.from_user.id)
    if s is None:
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
            logger.warning(str(message.from_user.id) + " set language " + language_name)
            language_name = language_name[1:]
        if language_name.lower() not in LANGS:
            await message.reply("Sorry, can't recognize the language name. Make sure it's correct and is *in English* "
                                "(e.g. instead of _Deutsch_ use _German_).")
            return
        await message.reply("Language is set to *" + language_name.title() + "*")
        await bot.send_message(message.from_user.id, "Now you can /addwords to /learn")
        logger.info(str(message.chat.id) + " learns " + language_name)
        s.set_active_language(language_name.lower())
        logger.debug(s.active_lang())
        with open('sessions.pkl', 'wb') as f:
            pickle.dump(sessions, f)
        s.status = None


# ==========================================================================================
# Adding new words

# Getting the command, setting s.status ="/addwords"
@dp.message_handler(commands=['addwords'])
async def addwords_message(message):
    logger.info(str(message.from_user.id) + " started adding new words")
    command = str(message.text)
    s = await get_session(message.from_user.id)
    if s is None:
        return
    if s.active_lang() is None:
        await message.reply("First, select language to learn with /setlanguage")
        return
    lists_to_add = mysql_connect.lists_to_add(message.from_user.id, s.active_lang())
    if len(lists_to_add) > 0:
        word_list = str(lists_to_add[0][0])
        s.list_hid_word = (word_list, None, None)
        k = to_one_row_keyboard(['Add words', 'Not now'], [0,0], ["next_word_from_list","skip_list"])
        await bot.send_message(message.from_user.id,
                         "You have words to add from list *{}*".format(word_list.title()),
                         reply_markup=k)
    else:
        s.status = "/addwords"
        s.words_to_add = None
        if command != "/addwords":
            logger.warning(str(message.from_user.id) + " put words after /addwords ")
        logger.debug(str(message.from_user.id) + s.status)
        await message.reply("Type in words in *" + s.active_lang().title() + "*")


def user_state(user_id, state):
    if user_id not in sessions.keys():
        return False
    return sessions[user_id].status == state

@dp.callback_query_handler(posts_cb.filter(action=["skip_list"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    s = await get_session(query.from_user.id)
    if s is None:
        return
    s.status = "/addwords"
    s.words_to_add = None
    s.list_hid_word = None
    logger.debug(str(query.from_user.id) + s.status)
    await bot.send_message(query.from_user.id, "Type in words in *" + s.active_lang().title() + "*")

# Getting a new word typed in by a user and getting definitions
@dp.callback_query_handler(posts_cb.filter(action=["wiktionary_search"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    message = query.message.reply_to_message
    await wiktionary_search(message)


@dp.message_handler(lambda message: user_state(message.from_user.id, "/addwords"))
async def wiktionary_search(message):
    user_id = message.from_user.id
    logger.debug(str(user_id) + " Adding word: " + message.text)
    logger.info(str(user_id) + " Sending request to Wiktionary")
    s = await get_session(user_id)
    if s is None:
        return
    begin = time.time()
    definitions = get_definitions(s.active_lang(), message.text)
    logger.info(str(user_id) + " Received response from Wiktionary " + str(time.time() - begin))
    logger.debug(str(user_id) + " Received definitions: " + str(definitions))
    s.words_to_add = (message.text, definitions)
    if len(definitions) == 0:
        logger.info(str(user_id) + " no definition found")
        await message.reply("No definitions found. Make sure there is no typos in the word and the language you're "
                            "learning exists))")
        kb = to_one_row_keyboard(["Add definition", "Skip"],
                                 data=[0, 1],
                                 action=["add_user_definition", "add_user_definition"])
        await bot.send_message(message.chat.id,
                               "Or you can add your own definition", reply_markup=kb)
    else:
        s.definitions = definitions
        await prepare_definition_selection(user_id, None)


async def add_word_to_storage(user_id, word, definition):
    s = await get_session(user_id)
    if s is None:
        return
    hid = sr.add_item((user_id, s.active_lang()), (word, definition), 0)
    mysql_connect.insert_word(user_id, s.active_lang(), word, definition, 0, hid)


# building up inline keybard
async def prepare_definition_selection(user_id, query):
    logger.debug(str(user_id) + " prepare_definition_selection")
    s = await get_session(user_id)
    if s is None:
        return
    definitions = s.definitions
    definitions = truncate(definitions,
                           30)  # FIXME ideally, it should be called once, not every time the keyboard is built
    actions = ['meaning'] * len(definitions)
    actions.append('add_user_definition')

    button_titiles = definitions
    button_titiles.append("ADD YOUR DEFINITION")

    if s.list_hid_word is None:
        button_titiles.append("CLOSE")
        actions.append('finish_adding_meanings')
    else:
        button_titiles.append("NEXT")
        actions.append('next_word_from_list')
        button_titiles.append("FINISH")
        actions.append('finish_adding_meanings')

    # k = to_vertical_keyboard(definitions, action=actions, data=list(range(0, len(actions), 1)))
    k = to_vertical_keyboard(definitions, action=actions, data=[0] * len(actions))
    if query is None:
        await bot.send_message(user_id, "Select a meaning to learn", reply_markup=k, parse_mode=types.ParseMode.MARKDOWN)
    else:
        await bot.edit_message_reply_markup(user_id, query.message.message_id, reply_markup=k)


# Adding selected definition
@dp.callback_query_handler(posts_cb.filter(action=["meaning"]))
async def callback_add_meaning_action(query: types.CallbackQuery, callback_data: dict):
    user_id = query.from_user.id
    logger.info(str(user_id) + ' Got this callback data: %r', callback_data)

    s = await get_session(query.from_user.id)
    if s is None:
        return
    n = int(callback_data.get('data'))
    if s.words_to_add is not None:
        word = s.words_to_add[0]
    else:
        logger.error(str(user_id) + ", s.words_to_add is None")
        await bot.send_message(user_id, RESTART)
        return
    try:
        definition = s.words_to_add[1][n]
    except IndexError as e:
        logger.warning(e)
        await bot.send_message(user_id, RESTART)
        return
    # s.words_to_add = None # Not needed for multiple definitions
    del s.definitions[n]
    logger.info(str(user_id) + " Adding new word: " + word + " - " + definition)
    await add_word_to_storage(query.from_user.id, word, definition)
    await query.answer("Definition added")
    await prepare_definition_selection(user_id, query)


@dp.callback_query_handler(posts_cb.filter(action=["add_user_definition"]))
async def callback_add_user_definition_action(query: types.CallbackQuery, callback_data: dict):
    logger.debug('callback_add_user_definition_action Got this callback data: %r', callback_data)
    await query.answer()
    s = await get_session(query.from_user.id)
    if s is None:
        return
    if callback_data.get('data') == "1":
        await bot.send_message(query.from_user.id, "OK, skipping")
        if s.list_hid_word is not None:
            await adding_list_words(None, query, None)
    else:
        s.status = 'adding_user_definition'
        word = s.words_to_add[0]
        await bot.send_message(query.message.chat.id,
                               "Type in your definition for {}".format(word),
                               reply_markup=types.ForceReply())



@dp.message_handler(lambda message: user_state(message.from_user.id, "adding_user_definition"))
async def adding_words(message):
    s = await get_session(message.from_user.id)
    if s is None:
        return
    definition = message.text
    word = s.words_to_add[0]
    s.words_to_add = None
    logger.debug(word + ": " + definition)
    await add_word_to_storage(user_id=message.from_user.id,
                              word=word,
                              definition=definition)
    s.status = "/addwords"
    if s.list_hid_word is not None:
        await adding_list_words(message, None, None)
    else:
        await bot.send_message(message.from_user.id, "OK")


@dp.callback_query_handler(posts_cb.filter(action=["finish_adding_meanings"]))
async def finish_adding_meanings_action(query: types.CallbackQuery, callback_data: dict):
    user_id = query.from_user.id
    logger.info(str(user_id) + ' Finished adding definitions. Got this callback data: %r', callback_data)
    s = await get_session(query.from_user.id)
    if s is None:
        return
    s.words_to_add = None
    s.definitions = list()
    s.status = "/addwords"
    s.adding_list=False
    await bot.edit_message_text(chat_id=user_id, message_id=query.message.message_id,
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
    logger.debug(str(message.from_user.id) + " Received message unknown message")
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
    s = await get_session(message.from_user.id)
    if s is None:
        return
    s.words_to_add = (t,)
    k = to_vertical_keyboard(buttons, action=actions, data=data)
    await message.reply("What would you like to do with this word?", reply_markup=k)


if __name__ == '__main__':
    print(sys.argv[1:])
    with open('lang.list') as f:
        LANGS = f.readlines()
    LANGS = [x.replace('\n', '').lower() for x in LANGS]
    executor.start_polling(dp, skip_updates=True)
