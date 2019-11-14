from loguru import logger

from bot.app.core import authorize, bot
from bot.app.learn.control import start_learning
from bot.bot_utils import mysql_connect
from bot.speech import text2speech
from bot.bot_utils import spaced_repetition as sr


async def do_text_summary_action(query):
    logger.info("{} received do_text_summary query", query.from_user.id)
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    summary = session.words_to_learn[0][0]
    await bot.send_message(query.from_user.id,
                           "*LISTEN* and *READ* aloud the summary:\n{}".format(summary))
    voice = text2speech.get_voice(summary, session.active_lang())
    await bot.send_audio(chat_id=session.get_user_id(),
                                     audio=voice,
                                     performer='Listen and repeat', caption=None,
                                     title='Summary')


async def do_text_words_action(query):
    # FIXME: duplicates code from conrol.py learning
    logger.info("{} received do_text_words query", query.from_user.id)
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    list_name = session.get_current_word()[1]
    hids = mysql_connect.get_hids_for_list(query.from_user.id, list_name)
    hids_all = sr.get_items_to_learn(
            (session.get_user_id(), session.active_lang()),
            upper_recall_limit=1)
    hids = list(set(hids) & set(hids_all))
    words = mysql_connect.fetch_by_hids(session.get_user_id(), hids)
    session.words_to_learn = words
    session.current_word = 0
    await start_learning(session)