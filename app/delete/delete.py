from loguru import logger
from aiogram import types

import mysql_connect
from app.core import authorize, bot
from bot_utils import to_one_row_keyboard


async def delete_command(message: types.Message):
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    logger.info(str(session.get_user_id()) + ' /delete command')
    session.status = "delete"
    await message.reply('Write the word you want to delete')


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


async def delete_action(query: types.CallbackQuery, callback_data: dict):
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


async def keep_action(query: types.CallbackQuery, callback_data: dict):
    await query.answer()
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    logger.info(str(session.get_user_id()) + ' is keeping word ' + session.hid_cash)
    session.hid_cash = ""
    await bot.send_message(session.get_user_id(), "OK, let's keep it")

