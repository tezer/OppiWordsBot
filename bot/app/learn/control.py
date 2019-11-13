import re

from aiogram import types

from bot import ilt
from bot.app.core import bot, authorize, get_session, RESTART
from bot.bot_utils.bot_utils import to_one_row_keyboard, to_vertical_keyboard, get_hint
from bot.ilt import sort_words, tasks, level_up
from bot.bot_utils import spaced_repetition as sr, mysql_connect
from bot.app.learn import reading, syntaxis, texts
from loguru import logger

from bot.speech import text2speech


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
    hids = sr.get_items_to_learn(
        (session.get_user_id(), session.active_lang()), upper_recall_limit=0.5)

    lists = mysql_connect.get_list_names(message.from_user.id)
    keys = ['Learn all words (use /stop to finish learning)']
    data = [-1]
    actions = ["start_learning"]
    await bot.send_message(session.get_user_id(), "You have {} words to learn.\n".format(len(hids)))
    if len(lists) > 0:
        keys.extend(lists)
        data.extend(list(range(len(lists))))
        actions.extend(["start_learning"] * len(lists))
        await bot.send_message(session.get_user_id(), "You have {} lists to learn.\n"
                               .format(len(lists)))

    kb = to_vertical_keyboard(keys, data=data, action=actions)
    await bot.send_message(session.get_user_id(), "What do you want to learn now?",
                           reply_markup=kb)


async def learn_sentences(user, list_name, session, hids):
    await bot.send_message(user, "You've leaned all the words from list _{}_. "
                                 "Now let's do some grammar exercises.".format(list_name))
    # 0. word, 1. definition, 2. mode, 3. hid
    # 0. sentence, 1. translation, 2. mode, 3. hid
    sentences = mysql_connect.fetch_sentences(session.get_user_id(), list_name)
    sent_to_learn = list()
    if hids is not None:
        for s in sentences:
            if s[3] in hids:
                sent_to_learn.append(s)
    else:
        sent_to_learn = sentences
    session.words_to_learn = sent_to_learn
    session.current_word = 0
    await start_learning(session)


async def learn_text(user, list_name, session):
    await bot.send_message(user, "You've leaned all the words and sentences from list _{}_. "
                                 "Now let's do some text.".format(list_name))

    await texts.text_summarization(user, list_name, session)


async def learning(query: types.CallbackQuery, callback_data: dict):
    await query.answer("Let's learn!")
    logger.debug(query)
    logger.debug(str(query.from_user.id)
                 + "start_learning  " + str(callback_data))
    n = int(callback_data['data'])
    session, isValid = await authorize(query.from_user.id, with_lang=True)
    if not isValid:
        return
    upper_recall_limit = 0.5
    if session.status == '/test':
        upper_recall_limit = 1.0
    if n == -1:  # General vocabulary selected
        hids = sr.get_items_to_learn(
            (session.get_user_id(), session.active_lang()),
            upper_recall_limit=upper_recall_limit, n=n)
        if len(hids) == 0:
            if session.status == '/test':
                await bot.send_message(session.get_user_id(),
                                       'You should add at least one word with /addwords command to start training')
            else:
                await bot.send_message(session.get_user_id(), 'You don\'t have words for training.')
                await bot.send_message(session.get_user_id(), 'Add more words with /addwords command or')
                await bot.send_message(session.get_user_id(), 'or /test words you learned before.')
            return True
    sentences = False
    if n >= 0:  # One of the lists selected
        lists = mysql_connect.get_list_names(query.from_user.id)
        list_name = lists[int(callback_data['data'])]
        logger.info("{} learns {}", query.from_user.id, list_name)
        hids = mysql_connect.get_hids_for_list(query.from_user.id, list_name)
        hids_all = sr.get_items_to_learn(
            (session.get_user_id(), session.active_lang()),
            upper_recall_limit=upper_recall_limit, n=n)
        # hids = list(set(hids) & set(hids_all))
        hids = list() #FIXME NOW delete after testing!!!
        if len(hids) == 0:
            sentence_hids = mysql_connect.get_sentence_hids(query.from_user.id, list_name)
            sentence_hids = ilt.get_objects(sentence_hids, '1 day', session.get_user_id(),
                                            session.active_lang(), "SENTENCE", 10)
            sentences = True
            if len(sentence_hids) > 0:
                session.current_level = 10 #Syntax learning
                await learn_sentences(query.from_user.id, list_name, session, sentence_hids)
            else:
                session.current_level = 20 #Text learning
                await learn_text(query.from_user.id, list_name, session)

    if not sentences:
        words = mysql_connect.fetch_by_hids(session.get_user_id(), hids)
        session.words_to_learn = words
        session.current_word = 0

        if not session.has_more_words_to_learn():
            # Case 2: doing reading errors
            await bot.send_message(session.get_user_id(), "Let's revise some words")
            await reading.do_reading_errors(query, callback_data)
        else:
            # Case 1: reading exercises
            await start_learning(session)


# Get reply from the user and filter the data: set number and shuffle
async def start_learning(session):
    words = session.words_to_learn
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
            session.current_level = word[2]
            logger.debug("{} started level {}", session.get_user_id(), word[2])
            keyboard = to_one_row_keyboard(["I remember", "Show meaning"],
                                           data=[0, 1],
                                           action=["I_remember", "show"])
            hint = get_hint(word[1])

            contexts = mysql_connect.get_context_by_hid(word[3])
            word_context = ''
            if contexts is not None:
                for context in contexts:
                    word_context += re.sub(r'\b' + word[0] + r'\b',
                                           '<b>' + word[0] + '</b>',
                                           context,
                                           flags=re.I)
                    word_context += '\n'
            if len(word_context) == 0:
                word_context = '<b>' + word[0] + '</b>'
            await bot.send_message(session.get_user_id(), word_context + "\n" + hint,
                                   reply_markup=keyboard, parse_mode=types.ParseMode.HTML)
        elif word[2] == 2:
            session.current_level = word[2]
            logger.debug("{} started level {}", session.get_user_id(), word[2])
            if session.subscribed:
                logger.debug("{} is subscribed", session.get_user_id())
                session.status = tasks[2]
                await bot.send_message(session.get_user_id(), "*SAY* this word: *" + word[1] + "*")
            else:
                level_up(session)
                await do_learning(session)
        elif word[2] == 3:
            session.current_level = word[2]
            logger.debug("{} started level {}", session.get_user_id(), word[2])
            if session.subscribed:
                logger.debug("{} is subscribed", session.get_user_id())
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
            session.current_level = word[2]
            logger.debug("{} started level {}", session.get_user_id(), word[2])
            session.status = tasks[1]
            await bot.send_message(session.get_user_id(),
                                   "*WRITE* the correct word for the definition:\n*" + word[1] + "*")
        # SENTENCES
        # Unscramble
        elif word[2] == 10:
            session.current_level = word[2]
            logger.debug("{} started level {}", session.get_user_id(), word[2])
            await syntaxis.unscramble(session, word)
