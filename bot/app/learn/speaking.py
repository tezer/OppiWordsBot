from bot.app.core import authorize, bot, TOKEN
from loguru import logger
from aiogram import types

from bot.app.learn.control import do_learning
from bot.bot_utils.bot_utils import compare
from bot.ilt import level_up
from bot.speech import speech2text


async def voice_message(message: types.Message):
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    logger.info(str(message.from_user.id) + ' voice message received')
    if not session.subscribed:
        await bot.send_message(message.from_user.id, "You need to buy subscription "
                                                     "to be able to use voice recognition."
                                                     "\n Use command /subscribe to buy subscription")

        return
    file = await bot.get_file(message.voice.file_id)
    url = 'https://api.telegram.org/file/bot{}/'.format(TOKEN)
    url = url + file["file_path"]
    logger.debug("{} received voice at {}".format(message.from_user.id, url))
    transcript = speech2text.transcribe(url, session.active_lang())
    if session.get_current_word() is None:
        await bot.send_message(message.from_user.id, "Start /learn or /test")
        return
    word = session.get_current_word()[0]
    if transcript.lower() != word.lower():
        word, transcript = compare(word.lower(), transcript.lower())
        print(word, transcript)
        await bot.send_message(message.from_user.id, "Correct word: {}\n"
                                                     "Transcript:     {}".format(word, transcript),
                               parse_mode=types.ParseMode.HTML)
    else:
        level_up(session)
        await bot.send_message(message.from_user.id, "Excellent!")
    await do_learning(session)
