from loguru import logger
from aiogram import types

from bot.bot_utils import mysql_connect
from bot.app.core import authorize, bot
from bot.bot_utils.bot_utils import to_one_row_keyboard, to_vertical_keyboard


async def delete_list(session):
    keys = mysql_connect.get_list_names(session.get_user_id())
    data = list(range(len(keys)))
    actions = ["delete_list"] * len(keys)
    keys.append("CANCEL")
    data.append(-1)
    actions.append("keep_list")
    k = to_vertical_keyboard(keys, data, actions)
    await bot.send_message(session.get_user_id(), "Which list do you want to delete?",
                           reply_markup=k)


async def delete_list_action(query, callback_data):
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    lists = mysql_connect.get_list_names(session.get_user_id())
    list_name = lists[int(callback_data['data'])]
    keys = ['DELETE the list, KEEP the words', 'DELETE the list, DELETE al its words',
                              'CANCEL']
    data = [callback_data['data']]*3
    actions = ['del_list_keep_words', 'del_list_del_words', "keep_list"]
    k = to_vertical_keyboard(keys, data, actions)
    await bot.send_message(query.from_user.id, "You are about to delete list *{}*\nDo you want to delete all the words in the list? "
                           "Or should I keep the words and delete the list only?".format(list_name),
                           reply_markup=k)

async def del_list_keep_words(query, callback_data):
    lists = mysql_connect.get_list_names(query.from_user.id)
    list_name = lists[int(callback_data['data'])]
    mysql_connect.del_list_keep_words(query.from_user.id, list_name)
    await bot.send_message(query.from_user.id, "{} is deleted. "
                                               "Word are saved to the general list".format(list_name))


async def del_list_del_words_action(query, callback_data):
    lists = mysql_connect.get_list_names(query.from_user.id)
    list_name = lists[int(callback_data['data'])]
    mysql_connect.del_list_del_words(query.from_user.id, list_name)
    await bot.send_message(query.from_user.id, "{} is deleted.".format(list_name))



async def delete_command(message: types.Message):
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    logger.info(str(session.get_user_id()) + ' /delete command')
    session.status = "delete"
    if message.text == "/delete list":
        await delete_list(session)
    else:
        await message.reply('Write the word you want to delete')


async def deleting_word(message):
    session, isValid = await authorize(message.from_user.id, with_lang=True)
    if not isValid:
        return
    logger.info(str(session.get_user_id())
                + " is deleting word " + message.text)
    data = mysql_connect.fetchall("SELECT word, definition, hid FROM words "
                                  "WHERE user=%s and language=%s and word=%s",
                                  (session.get_user_id(), session.active_lang(), message.text))
    session.status = ""
    if data is None:
        await bot.send_message(session.get_user_id(), 'The words does not exist in you dictionary')
        return
    session.hid_cash = list(x[2] for x in data)
    k = to_one_row_keyboard(["Keep", "Delete"], data=[
        0, 1], action=["keep", "delete"])
    await bot.send_message(session.get_user_id(), "Do you want to delete word *{}* with definition\n{}"
                           .format(data[0][0], data[0][1]), reply_markup=k)


async def delete_action(query: types.CallbackQuery, callback_data: dict):
    await query.answer()
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    logger.info('{} is deleting words {}', session.get_user_id(), session.hid_cash)
    result = mysql_connect.delete_by_hids(session.hid_cash)
    session.hid_cash = ""
    if result is None:
        await bot.send_message(session.get_user_id(), 'The word is deleted')
    else:
        logger.warning('{}  failed to delete word  {}', session.get_user_id(), result)
        await bot.send_message(session.get_user_id(), 'Failed to delete the word')


async def keep_list_action(query):
    await query.answer()
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    logger.info(str(session.get_user_id()) + ' is keeping list ')
    await bot.send_message(session.get_user_id(), "OK, let's keep it")


async def keep_action(query: types.CallbackQuery, callback_data: dict):
    await query.answer()
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    logger.info(str(session.get_user_id()) + ' is keeping word ' + session.hid_cash)
    session.hid_cash = ""
    await bot.send_message(session.get_user_id(), "OK, let's keep it")
