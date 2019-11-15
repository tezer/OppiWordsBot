from aiogram import types
from loguru import logger

from bot.app.core import bot, authorize
from bot.bot_utils import mysql_connect, bot_utils
from bot.speech import text2speech


async def para_summarization(session):
    para = session.get_current_word()
    await bot.send_message(session.get_user_id(),
                           'Rewrite this paragraph')
    await bot.send_message(session.get_user_id(),
                           para[0],
                           reply_markup=types.ForceReply())




async def text_summarization(user, list_name, session):
    session.list_name = list_name
    sentences = mysql_connect.fetch_sentences(user, list_name)
    if len(sentences) == 0:
        await bot.send_message(user, "Sorry, the text is missing. /learn something else or /addtext")
        return
    await bot.send_message(user, "You've leaned all the words and sentences from list _{}_. "
                                 "Now let's do some text.".format(list_name))
    await bot.send_message(user, "First, let's summarize the text.\n"
                                 "Rewrite each paragraph to make it shorter and simpler, "
                                 "keep only the most important information.\n"
                                 "To skip a paragraph just type a dot (.) and hit _Enter_.")
    paragraphs = list()
    para = str()
    for sentence in sentences:
        if sentence[0].endswith('\n'):
            para += sentence[0]
            paragraphs.append((para, '', 20, 0))
            para = ''
        else:
            para += sentence[0]
    session.words_to_learn = paragraphs
    session.current_word = 0
    session.status = "summarization"
    await para_summarization(session)


async def check_summary(session):
    summary = ''
    for para in session.words_to_learn:
        t = para[1]
        if len(t) < 2:
            continue
        summary += para[1] + '\n'
    session.words_to_learn = list()
    session.current_word = 0
    session.status = str()
    await bot.send_message(session.get_user_id(), "All done! Here is your summary:\n{}"
                           .format(summary))
    text_hid = mysql_connect.fetchone('SELECT text_hid FROM user_texts WHERE user=%s AND list_name=%s',
                                      (session.get_user_id(), session.list_name))
    args = (session.get_user_id(), text_hid[0], summary)
    mysql_connect.insertone('INSERT INTO text_summary (user, hid, summary)'
                            ' VALUES(%s,%s,%s)', args)
    voice = text2speech.get_voice(summary, session.active_lang())
    await bot.send_audio(chat_id=session.get_user_id(),
                                     audio=voice,
                                     performer='Listen and repeat', caption=None,
                                     title='Summary')


async def summarization_message(message):
    logger.info("{} received summarization_message", message.from_user.id)
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    para = session.get_current_word()
    para = (para[0], message.text, para[2], para[3])
    session.words_to_learn[session.current_word] = para
    session.current_word += 1
    if len(session.words_to_learn) == session.current_word:
        await check_summary(session)
    else:
        await para_summarization(session)