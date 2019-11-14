from loguru import logger

from bot.app.core import authorize, bot
from bot.speech import text2speech


async def do_text_summary_action(query):
    logger.info("{} received do_text_summary message", query.from_user.id)
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

