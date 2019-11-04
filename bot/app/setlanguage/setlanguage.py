import pickle

from loguru import logger
from bot.app.core import authorize, bot, LANGS, sessions
from aiogram import types

async def setlanguage_command_message(message: types.Message):
    logger.debug(message)
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    session.status = 'setlanguage'
    if " " in message.text or message.text != '/setlanguage':
        await setlanguage_message(message)
    else:

        forced_reply = types.ForceReply()
        await message.reply("Type the name of the language to learn (e.g. English, Finnish or other.\n"
                            "You can always change it with /setlanguage", reply_markup=forced_reply)


async def setlanguage_action(query: types.CallbackQuery, callback_data: dict):
    session, isValid = await authorize(query.from_user.id)
    if not isValid:
        return
    session.status = "setlanguage"
    await setlanguage_message(query.message.reply_to_message)


async def setlanguage_message(message):
    logger.debug("Received message")
    logger.debug(message)
    session, isValid = await authorize(message.from_user.id)
    if not isValid:
        return
    language_name = str(message.text)
    if language_name == "":
        await message.reply("OK, let's skip it for now")
    elif language_name.startswith("/setlanguage") and " " in language_name:
        language_name = language_name.split(" ", 1)[1]
    if " " in language_name:
        await message.reply("Language name is wrong. It must be one word only (e.g. _English_)")
    else:
        if language_name[0] == '/':
            logger.warning(str(message.from_user.id)
                           + " set language " + language_name)
            language_name = language_name[1:]
        if language_name.lower() not in LANGS:
            await message.reply("Sorry, can't recognize the language name. Make sure it's correct and is *in English* "
                                "(e.g. instead of _Deutsch_ use _German_).")
            return
        await message.reply("Language is set to *" + language_name.title() + "*")
        await bot.send_message(message.from_user.id, "Now you can /addwords to /learn")
        logger.info(str(message.chat.id) + " learns " + language_name)
        session.set_active_language(language_name.lower())
        logger.debug(session.active_lang())
        with open('sessions.pkl', 'wb') as f:
            pickle.dump(sessions, f)
        session.status = None