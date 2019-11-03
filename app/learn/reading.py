import random

from aiogram.utils.exceptions import CantParseEntities
from loguru import logger
from aiogram import types
from app.core import authorize, bot

from app.learn.control import do_learning1, do_learning
from bot_utils import to_vertical_keyboard, to_one_row_keyboard
from ilt import level_up


# Reading errors loop, end of the learning loop if no more words to learn
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


# reading task 1 answer "I remember"
async def i_remember(query: types.CallbackQuery, callback_data: dict):
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    level_up(session)
    n = len(session.words_to_learn) - session.current_word
    if n > 0:
        await query.answer(str(n) + " to go")
    await do_learning(session)




# reading task showing definition, adding word to the error list
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
