from datetime import datetime
import re

from aiogram import types

from bot.bot_utils import mysql_connect, smart_list, word_lists
from bot.app.addwords.addwords import wiktionary_search
from bot.app.core import authorize, bot, logger
from bot.bot_utils.bot_utils import to_vertical_keyboard


async def wordlist_command(message: types.Message):
    user_id = message.from_user.id
    logger.info(str(user_id) + ' /wordlist')
    session, isValid = await authorize(user_id, with_lang=True)
    if not isValid:
        return
    tokens = ["Top frequency words", "Smart list"]
    data = [0, 0]
    actions = ['topn', 'smart']
    k = to_vertical_keyboard(tokens=tokens, data=data, action=actions)
    await bot.send_message(session.get_user_id(), "What type of lists would you like?", reply_markup=k)


async def topn_action(query: types.CallbackQuery, callback_data: dict):
    session, isValid = await authorize(query.from_user.id, with_lang=True)
    if not isValid:
        return
    lang = session.active_lang().title()
    session.status = 'topn'
    m = query.message
    await m.edit_reply_markup()
    await m.edit_text("Type _0:100_ if you want to add top 100 most frequent words for {}"
                      "\nor _50:100_ if you want to skip top 50 words. You can specify any range in the format _start:end_"
                      "\nThe words don't have definitions. You will add them afterwards. ".format(lang))


async def smart_action(query: types.CallbackQuery, callback_data: dict):
    session, isValid = await authorize(query.from_user.id, with_lang=True)
    if not isValid:
        return
    lang = session.active_lang().title()
    m = query.message
    if lang.lower() not in smart_list.CODES.keys():
        await m.edit_reply_markup()
        await m.edit_text("Sorry, the Smart list does not support {}. You can get in touch with the bot developers "
                          "at *OppiWordsBotGroup* (https://t.me/OppiWords)".format(lang))
        return
    session.status = 'topn'
    await m.edit_reply_markup()
    await m.edit_text(
        "The bot will offer you words which are semantically related to the last 3 words you recently learned in {}.".format(
            lang))
    words = smart_list.get_list(query.from_user.id, lang)
    if len(words) > 0:
        list_name = "SmartList " + str(datetime.today().strftime('%Y-%m-%d'))
        await bot.send_message(session.get_user_id(),
                               "The list name is _{}_. {} words are ready to be added to your dictionary. /addwords to do so.".
                               format(list_name, len(words)))
        mysql_connect.add_list(user=str(session.get_user_id()),
                               word_list=words,
                               lang=session.active_lang(),
                               list_name=list_name)
        session.status = None
        await adding_list_words(None, query, list_name)
    else:
        logger.warning(str(session.get_user_id()) + " bot didn't find words to add")
        await bot.send_message(session.get_user_id(),
                               "Sorry, the bot failed to suggest words for the list. I'll double check if it really smart enough)")


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
        "The list name is _{}_.The words are ready to be added to your dictionary. /addwords to do so.".format(
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
        logger.warning("User is not authorized")
        return
    if session.list_hid_word is not None:
        hid = session.list_hid_word[1]
        list_name = session.list_hid_word[0]
        mysql_connect.delete_from_list(hid)
    session.status = '/addwords'
    # listname, hid, word, offset
    word_list = mysql_connect.get_list(
        session.get_user_id(), session.active_lang(), list_name)
    if len(word_list) == 0 and list_name is not None:
        await bot.send_message(session.get_user_id(), "You added all words from the list *{}*\n"
                                                      "Now you can /learn words".format(list_name.title()))
        session.list_hid_word = None
        return
    if list_name is None:
        logger.error("{}, list_name is None".format(session.get_user_id()))
        return
    list_hid = word_list[0][1]
    offset = word_list[0][3]
    translation_context = mysql_connect.get_context(list_hid, offset)
    translation = ''
    word = word_list[0][2]
    context = '<b>' + word + '</b>'
    if translation_context is not None and len(translation_context) > 0:
        if len(translation_context[0]) > 0:
            translation = '\n' + translation_context[0]
        if len(translation_context) > 1:
            context = re.sub(r'\b' + word + r'\b', '<b>' + word + '</b>', translation_context[1])

    m = await bot.send_message(session.get_user_id(),
                               "{} words to add from list <i>{}</i>{}\n{}".format(
                                   len(word_list), list_name.title(),
                                   translation, context),
                               parse_mode=types.ParseMode.HTML)
    session.list_hid_word = word_list[0]
    m.text = word
    m.from_user.id = session.get_user_id()
    await wiktionary_search(m)


async def next_word_action(query: types.CallbackQuery, callback_data: dict):
    await query.message.edit_reply_markup()
    await query.message.edit_text("Next word")
    await adding_list_words(None, query, None)
