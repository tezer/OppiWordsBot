import sys

from expiringdict import ExpiringDict
from loguru import logger
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from bot.bot_utils import mysql_connect
from bot.bot_utils import user_stat
from bot.usersession import UserSession
from settings import bot_token, db_conf

logger.add("oppiwordsbot_{time}.log")

TOKEN = bot_token[sys.argv[1:][0]]
bot = Bot(token=TOKEN,
          parse_mode=types.ParseMode.MARKDOWN)
db_conf = db_conf[sys.argv[1:][0]]
user_stat.conf = db_conf

mem_storage = MemoryStorage()
dp = Dispatcher(bot, storage=mem_storage)
RESTART = '"Sorry, something went wrong. Try restarting with /start, your progress is saved"'
with open('bot/app/lang.list') as f:
    LANGS = f.readlines()
LANGS = [x.replace('\n', '').lower() for x in LANGS]


sessions = ExpiringDict(max_len=2000, max_age_seconds=60 * 60 * 24)


async def get_session(user_id):
    if user_id in sessions.keys():
        return sessions[user_id]
    else:
        s = await create_user_session(user_id)
        return s


async def authorize(user_id, with_lang=False):
    session = await get_session(user_id)
    if session is None:
        return session, False

    if with_lang and (session.active_lang() is None):
        await bot.send_message(user_id, "You need to /setlanguage first")
        return session, False
    return session, True


def user_state(user_id, state):
    if user_id not in sessions.keys():
        return False
    if sessions[user_id] is None:
        return None
    return sessions[user_id].status == state



async def create_user_session(user):
    user_data = mysql_connect.fetchone("SELECT language_code, learning_language, first_name, last_name "
                            "FROM users WHERE user_id = %s",
                                (user, ))
    if user_data is None:
        logger.info("{} has now session in db", user)
        await bot.send_message(user, "You should /start the bot before learning")
        return

    if user_data[0] is None:
        user_data = ('english', user_data[1])
        await bot.send_message(user, 'Please, run /settings to specify your language')

    if user_data[1] is None:
        await bot.send_message(user, 'Please, run /setlanguage to specify the language you want to learn')
        user_data = (user_data[0], 'english')

    s = UserSession(user, user_data[2],
                    user_data[3],
                    user_data[0])
    s.subscribed = mysql_connect.check_subscribed(user)
    s.set_active_language(user_data[1])
    logger.info("{} session is ready, subscription status is {}", user, s.subscribed)
    sessions[user] = s
    return s