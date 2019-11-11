import re

from loguru import logger
from aiogram import types

from bot.bot_utils import mysql_connect
from bot.bot_utils import bot_utils
from bot.app.core import authorize, bot, get_session
import os
import settings

os.environ["POLYGLOT_DATA_PATH"] = settings.polyglot_env
from polyglot.text import Text

CODES = {
    'finnish': 'fi',
    'german': 'de',
    'english': 'en',
    'italian': 'it',
    'estonian': 'et',
    'thai': 'th',
    'japanese': 'ja',
    'spanish': 'es',
    'french': 'fr'

}


async def add_text_command(message: types.Message):
    user_id = message.from_user.id
    logger.info(str(user_id) + ' /addtext')

    session, isValid = await authorize(user_id, with_lang=True)
    if not isValid:
        return
    await bot.send_message(user_id, "Paste in a short text here.")
    session.status = "text_added"


from multi_rake import Rake


class TextPreprocessor(object):

    def __init__(self, lang=None):
        self.lang = lang
        self.rake = Rake(language_code=self.lang, max_words=5)

    def key_words(self, text):
        return self.rake.apply(text)


class BotSentence(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.translation = ""
        self.words = list()
        self.hids = list()


class BotText(object):
    def __init__(self, text):
        self.text = text
        self.sentences = list()
        self.name = str()

    def get_string(self, start, end):
        return str(self.text)[start:end]


def get_words_and_phrases(text, text_language, user_language):
    sentences = list()
    processor = TextPreprocessor(CODES[text_language])
    # TODO save to cache the processors
    t = Text(text)
    for s in t.sentences:
        sent = BotSentence(s.start, s.end)
        # TODO paid feature
        translation = bot_utils.get_definitions(text_language, user_language, s.string)
        sent.translation = translation
        key_words = processor.key_words(s.string)
        for kw in key_words:
            w = kw[0]
            if ' ' in w:
                sent.words.append(w)
        for word in s.words:
            word = str(word)
            if re.match(r"[^\w]+", word) is not None:
                continue
            sent.words.append(word)
        sentences.append(sent)

    return sentences


async def add_sentences(text, session, hid):
    for s in text.sentences:
        sentence_text = text.get_string(s.start, s.end)
        sent_hid = mysql_connect.add_sentence(sentence_text, s.start, s.end, hid)
        mysql_connect.add_sentence_translation(s.translation[0], sent_hid, session.language_code)
        for w in s.words:
            mysql_connect.add_text_word(w, sent_hid, session.active_lang(), session.user_id,
                                        text.name)


async def add_text(message: types.Message):
    user_id = message.from_user.id
    logger.info(str(user_id) + ' /addtext received')
    session = await get_session(user_id)
    if session is None:
        return
    sentences = get_words_and_phrases(message.text, session.active_lang(), session.language_code)
    text_name = str(message.text).split('\n')[0][:30]
    text = BotText(message.text)
    text.sentences = sentences
    text.name = text_name

    session.status = None
    hid = mysql_connect.add_text(session.active_lang(), message.text)
    mysql_connect.add_user_text(user_id, hid, text_name)
    await add_sentences(text, session, hid)
    await bot.send_message(session.get_user_id(), (
        "The text name is _{}_.\nThe words are ready to be added to your dictionary. "
        "Use /addwords command to start adding the words.".format(
            text_name)))
