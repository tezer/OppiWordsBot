import time

from loguru import logger
from aiogram import types

from bot.bot_utils import mysql_connect
from app.core import authorize, bot

async def show_command(message: types.Message):
    logger.info(str(message.from_user.id) + ' ' + str(message.text))

    session, isValid = await authorize(message.from_user.id, with_lang=True)
    if not isValid:
        return

    cmd = message.text
    if ' ' in cmd:
        cmd2 = str(cmd).split(' ')
        if cmd2[1] == 'list':
            # TODO ask for list name and show words from the list
            pass
        elif cmd2[1] == 'date':
            words = mysql_connect.fetchall(
                "SELECT w.word, w.definition, DATE_FORMAT(s.created_at, '%Y-%m-%d') AS date FROM words w INNER JOIN spaced_repetition s ON w.hid = s.hid WHERE w.user =%s AND w.language=%s AND w.mode = 0 ORDER BY date",
                (session.get_user_id(), session.active_lang()))
        elif cmd2[1] == 'last':
            LIMIT = ""
            if len(cmd2) == 3:
                n = cmd2[2]
                LIMIT = ' LIMIT ' + str(n)

            words = mysql_connect.fetchall(
                "SELECT w.word, w.definition, DATE_FORMAT(s.created_at, '%Y-%m-%d') AS date FROM words w INNER JOIN spaced_repetition s ON w.hid = s.hid WHERE w.user =%s AND w.language=%s AND w.mode = 0 ORDER BY date DESC" + LIMIT,
                (session.get_user_id(), session.active_lang()))
        else:
            letter = str(cmd2[1]) + '%'
            words = mysql_connect.fetchall(
                "SELECT word, definition FROM words WHERE user =%s AND language=%s AND mode = 0 AND word LIKE %s ORDER BY word",
                (session.get_user_id(), session.active_lang(), letter))

    else:
        words = mysql_connect.fetchall(
            "SELECT word, definition FROM words WHERE user=%s AND language=%s AND mode = 0 ORDER BY word",
            (session.get_user_id(), session.active_lang()))

    for w in words:
        date_str = ""
        if len(w) == 3:
            date_str = "\n" + str(w[2])
        await bot.send_message(session.get_user_id(), "<b>{}</b> : {}".format(w[0], w[1]) + date_str,
                               parse_mode=types.ParseMode.HTML, disable_notification=True)
        time.sleep(.1)
    await bot.send_message(session.get_user_id(), "Total: {} words".format(len(words)))

