import random

from bot.app.core import bot, authorize
from bot.app.learn import control
from bot.bot_utils import bot_utils
from loguru import logger
from aiogram import types

from bot.ilt import add_event


async def unscramble_message(query, callback_data):
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    revealed = session.unscramble_revealed
    m = query.message
    new_data = list()
    new_keys = list()
    for i in range(len(session.unscramble_data)):
        n = session.unscramble_data[i]
        if n == int(callback_data['data']):
            revealed = revealed + ' ' + session.unscramble_keys[i]
            continue
        new_data.append(n)
        new_keys.append(session.unscramble_keys[i])
    await do_unscramble(session, new_keys, new_data, session.unscramble_sentence, revealed, m)


async def restart_unscramble_message(query, callback_data):
    logger.info("{} restarts unscramble")
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    await unscramble(session, session.unscramble_sentence)



async def next_unscramble_message(query):
    logger.info("{} starts next unscramble")
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    await next_unscramble(session)


async def next_unscramble(session):
    #TODO save progress over sentences
    session.delete_current_word()
    session.unscramble_keys = None
    session.unscramble_data = None
    session.unscramble_revealed = None
    session.unscramble_sentence = None
    await control.do_learning(session)


async def do_unscramble(session, keys, data, sentence, revealed, message):
    logger.debug("{}: Keys = {}, revealed = {}", session.get_user_id(),
                 len(keys), revealed)
    if len(keys) == 0 and len(revealed) > 0:
        if revealed.strip() == session.unscramble_sentence[0].strip():
            add_event(message.from_user.id, session.get_current_hid(), 'SENTENCE', 10, 1)
            await bot.send_message(session.get_user_id(), "Excellent!")
            await next_unscramble(session)
        else:
            k = bot_utils.to_one_row_keyboard(['Restart', 'Next'],
                                              [0, 1],
                                              ['restart_unscramble', 'next_unscramble'])
            res = bot_utils.compare(revealed.strip(), session.unscramble_sentence[0].strip())
            #TODO use Levenshtian distance
            add_event(message.from_user.id, session.get_current_hid(), 'SENTENCE', 10, 0)
            await bot.send_message(session.get_user_id(), "A bit wrong.\nIt is:\n"
                                                        "{}\nyuor answer:\n{}"
                                   .format(res[1], res[0]), parse_mode=types.ParseMode.HTML,
                                   reply_markup=k)
        return
    actions = ['unscramble'] * len(data)
    session.unscramble_keys = keys
    session.unscramble_data = data
    session.unscramble_revealed = revealed
    session.unscramble_sentence = sentence

    k = keys.copy()
    k.append("RESTART")
    a = actions.copy()
    a.append("restart_unscramble")
    d = data.copy()
    d.append('-1')
    k = bot_utils.to_vertical_keyboard(k, d, a)
    await message.edit_text("*" + sentence[1] + "*" + "\n" + revealed, reply_markup=k)



async def unscramble(session, sentence):
    m = await bot.send_message(session.get_user_id(),
                               "Put the words in correct order")
    tokens = sentence[0].split(' ')
    keys = list()
    data = list()
    action = list()
    for i in range(len(tokens)):
        token = tokens[i].strip()
        if len(token) == 0:
            continue
        keys.append(token)
        data.append(i)
        action.append('unscramble')
    c = list(zip(keys, data))
    random.shuffle(c)
    keys, data = zip(*c)
    k = list(keys)
    d = list(data)
    await do_unscramble(session, k, d, sentence, "", m)
