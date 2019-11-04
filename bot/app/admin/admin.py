import time

from loguru import logger

from bot.bot_utils import mysql_connect, user_stat
from settings import admin
from app.core import bot
from aiogram import types
from aiogram.utils.exceptions import BotBlocked as Blocked

async def send_notifications_to_users(message: types.Message):
    user_id = message.from_user.id
    if user_id != admin:
        logger.error("Wrong admin: " + str(user_id))
        await bot.send_message(admin, "Wrong admin: " + str(user_id))
        return
    notifications = user_stat.get_user_message(24)
    logger.warning(
        "sending {} notifications to users".format(len(notifications)))
    await bot.send_message(admin, "sending {} notifications to users".format(len(notifications)))
    blocked = 0
    for user_id, notification_text in notifications.items():
        time.sleep(.5)
        # user_id = admin #USE FOR TESTING
        try:
            logger.debug("Sending notification to " + str(user_id))
            await bot.send_message(user_id, notification_text, parse_mode=types.ParseMode.HTML)
        except Blocked as e:
            print(e)
            logger.warning("User {} blocked the bot".format(user_id))
            blocked += 1
            mysql_connect.update_blocked(user_id)
        except Exception as e:
            logger.error("Error sending notification: " + str(e))
    await bot.send_message(admin, str(blocked) + " users blocked the bot")