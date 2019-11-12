from bot.app.core import bot


async def do_text(session, text):
    words = list(x[0] for x in session.words_to_learn)
    words_line = ', '.join(words)
    await bot.send_message(session.get_user_id(), 'Read this text:\n{}'.format(text))
    await bot.send_message(session.get_user_id(), 'Summarize it using following words:\n'
                                                  '{}'.format(words_line))

    return None