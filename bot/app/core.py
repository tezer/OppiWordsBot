import sys

from expiringdict import ExpiringDict
from loguru import logger
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import pickle
from pathlib import Path

from bot.bot_utils import user_stat
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

#
# def load_data(name):
#     data_file = Path(name)
#     if data_file.is_file():
#         with open(name, 'rb') as f:
#             data_new = pickle.load(f)
#     else:
#         data_new = dict()
#     return data_new


# sessions = load_data("sessions.pkl")  # user_id: session
sessions = ExpiringDict(max_len=100, max_age_seconds=60 * 60 * 24)


async def get_session(user_id):
    if user_id in sessions.keys():
        return sessions[user_id]
    else:
        await bot.send_message(user_id, "You should /start the bot before learning")
        return None


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
    return sessions[user_id].status == state
