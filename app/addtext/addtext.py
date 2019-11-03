from loguru import logger
from aiogram import types

import mysql_connect
import word_lists
from app.core import authorize, bot, get_session
from app.wordlist import wordlist


async def add_text_command(message: types.Message):
    user_id = message.from_user.id
    logger.info(str(user_id) + ' /addtext')

    session, isValid = await authorize(user_id, with_lang=True)
    if not isValid:
        return
    m = await bot.send_message(user_id, "Paste in a short text here.")
    session.status = m.message_id + 1


async def add_text(message: types.Message):
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
    await wordlist.adding_list_words(message, None, list_name)
