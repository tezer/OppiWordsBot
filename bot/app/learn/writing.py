import time
from aiogram import types
from loguru import logger
from bot.bot_utils import spaced_repetition as sr
from bot.app.core import authorize, bot, RESTART
from bot.app.learn.control import do_learning1
from bot.bot_utils.bot_utils import compare
from bot.ilt import add_event


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
        # TODO do next word state, when it is available by task_transitions table
        sr.update_item(session.get_current_hid(), 1)
        add_event(message.from_user.id, session.active_lang(), session.get_current_hid(), 'LEXEME', 1, 1)
        session.delete_current_word()
        n = len(session.words_to_learn) - session.current_word
        if n > 0:
            await bot.send_message(session.get_user_id(), "*Correct!* *{}* to go".format(n))
        else:
            await bot.send_message(session.get_user_id(), "*Correct!* This was the last word.".format(n))
            logger.debug('last word')
        time.sleep(2)
    else:
        sr.update_item(session.get_current_hid(), 0)
        w1, w2 = compare(str(word).lower(), str(message.text).lower())
        #TODO add Levenshtain distance instead of '0'
        add_event(message.from_user.id, session.active_lang(), session.get_current_hid(), 'LEXEME', 1, 0)
        await bot.send_message(session.get_user_id(), "Wrong.\n"
                                                      "It should be: {}\n"
                                                      "you wrote:    {}".format(w1, w2),
                               parse_mode=types.ParseMode.HTML)
        time.sleep(3)
        misspelt_word = str(message.text)
        if word[0].isupper():
            misspelt_word = misspelt_word.capitalize()
        else:
            misspelt_word = misspelt_word.lower()
        session.add_writing_error(misspelt_word)
    session.status = None
    await do_learning1(session)
