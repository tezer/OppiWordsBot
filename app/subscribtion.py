from aiogram import types
from loguru import logger
from app.core import bot


async def help_message(message: types.Message):
    logger.info("{} try command", message.from_user.id)
    await message.reply("OK")
    await bot.send_message(message.from_user.id, "Hi")
