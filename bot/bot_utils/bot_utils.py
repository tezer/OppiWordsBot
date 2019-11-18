import json
import re
from wiktionaryparser import WiktionaryParser
from aiogram import types
from aiogram.utils.callback_data import CallbackData
from expiringdict import ExpiringDict

from bot.app.core import bot
from bot.bot_utils import mysql_connect
from bot.bot_utils.yandex_dictionary import YandexDictionary
import settings
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]= settings.google_env
from google.cloud import translate_v2
translate_client = translate_v2.Client()
import difflib
from loguru import logger


MEM_CACHE = ExpiringDict(max_len=100, max_age_seconds=6000)

key = settings.ya_key
ya_dict = YandexDictionary(key)

CODES = {'czech': 'cs',
         'danish': 'da',
         'dutch': 'nl',
         'english': 'en',
         'finnish': 'fi',
         'french': 'fr',
         'german': 'de',
         'greek': 'el',
         'hungarian': 'hu',
         'italian': 'it',
         'latvian': 'lv',
         'norwegian': 'no',
         'polish': 'pl',
         'portuguese': 'pt',
         'russian': 'ru',
         'spanish': 'es',
         'swedish': 'sv',
         'turkish': 'tr',
         'ukrainian': 'uk',
         }

parser = WiktionaryParser()
posts_cb = CallbackData('post', 'data', 'action')


def truncate(definitions, limit):
    result = list()
    for definition in definitions:
        d = definition
        if len(d) > limit:
            d = re.sub(r'^\([^\)]+\) *', "", d)
            if len(d) > limit:
                d = re.sub(r'\[[^\]]+\]', " ", d)
            if len(d) > limit:
                d = re.sub(r'\([^\)]+\)', " ", d)
            d = re.sub(r'  +', " ", d)
            d = re.sub(r' \.', ".", d)
        if d in result:
            result.append(definition)
        else:
            result.append(d)
    return result


def to_list(response):
    res = list()
    definitions = response['def']
    for d in definitions:
        translations = d['tr']
        for t in translations:
            ts = ''
            if 'ts' in t.keys():
                ts = ' [' + str(t['ts']) + '] '
            s = str(t['text']) + ' (' + t['pos'] + ') ' + ts
            res.append(s)
    return res


def process_wiktionary(w):
    result = list()
    for definition in w[0]['definitions']:
        pos = definition['partOfSpeech']
        for d in definition['text'][1:]:
            result.append(d + " (" + pos + ")")
    return result


def get_lang_code(user_lang):
    if user_lang in CODES.keys():
        return CODES[user_lang]
    if user_lang in CODES.values():
        return user_lang



async def get_definitions(language, user_lang, word, user):
    result = list()
    sources = mysql_connect.fetchall('SELECT source FROM def_sources WHERE user=%s', (user, ))
    sources = set(x[0] for x in sources)
    if user_lang is None:
        user_lang = 'english'
    # See list of available sources in generic.py
    if 'Yandex Dictionary' in sources:
        if 'Yandex Dictionary_' + user_lang + language + '_' + word in MEM_CACHE.keys():
            result = MEM_CACHE['Yandex Dictionary_' + user_lang + language + '_' + word]
        else:
            try:
                response = ya_dict.lookup(word, CODES[language], get_lang_code(user_lang))
                result = to_list(json.loads(response))
                MEM_CACHE['Yandex Dictionary_' + user_lang + language + '_' + word] = result

            except Exception as e:
                logger.warning("Yandex dictionary exception: " + str(e))

    if 'Wiktionary' in sources:
        if 'Wiktionary_' + language + '_' + word in MEM_CACHE.keys():
            result.extend(MEM_CACHE['Wiktionary_' + language + '_' + word])
        else:
            try:
                w = parser.fetch(word.lower(), language=language)
            except Exception as e:
                logger.warning("Wiktionary exception: " + str(e))

            if w is not None and len(w) > 0:
                res = process_wiktionary(w)
                if len(res) > 0:
                    result.extend(res)
                    MEM_CACHE['Wiktionary_' + language + '_' + word] = res
    if 'Google Translate' in sources or ' ' in word:
        if 'Google Translate_' + user_lang + language + '_' + word in MEM_CACHE.keys():
            result.extend(MEM_CACHE['Google Translate_' + user_lang + language + '_' + word])
        else:
            subscribed = mysql_connect.check_subscribed(user)
            limit = 50
            if subscribed:
                limit = 500
            if len(word) <= limit :
                try:
                    tr = translate_client.translate(
                        word,
                        target_language=get_lang_code(user_lang))
                    result.append(tr['translatedText'])
                    MEM_CACHE['Google Translate_' + user_lang + language + '_' + word] = tr['translatedText']
                except Exception as e:
                    logger.error(e)
    return result


def get_hint(text):
    hints = re.findall('\([^\)]+\)', text)
    l = list()
    for hint in hints:
        hint = str(hint).replace("(", " ")
        hint = str(hint).replace(")", " ")
        hint = str(hint).replace("  ", " ")
        l.append(hint.strip())
    return "; ".join(l)


def to_one_row_keyboard(tokens, data=None, action=None):
    keyboard = types.InlineKeyboardMarkup(action=action)
    text_and_data = list()
    for i in range(len(tokens)):
        t = tokens[i]
        a = action[i]
        d = data[i]
        text_and_data.append((t, d, a))
    row_btns = (types.InlineKeyboardButton(
        text, callback_data=posts_cb.new(data=data, action=a)) for text, data, a in text_and_data)
    keyboard.row(*row_btns)
    return keyboard


def to_vertical_keyboard(tokens, data=[], action=[]):
    keyboard = types.InlineKeyboardMarkup(action=action)
    for i in range(len(tokens)):
        t = tokens[i]
        keyboard.add(types.InlineKeyboardButton(t,
                                                callback_data=posts_cb.new(data=data[i],
                                                                           action=action[i])))
    return keyboard

#WORD DIFFERENCE =================================================================
def get_diff_ranges(blocks, index):
    result = list()
    start = 0
    for block in blocks:
        if index == 0:
            bl = block.a
        else:
            bl = block.b
        if bl == 0:
            start = block.size
            continue
        r = (start, bl)
        result.insert(0, r)
        start = bl + block.size
    return result


def mark_up(word, open, close, ranges):
    for r in ranges:
        a = word[:r[1]]
        b = word[r[1]:]
        word = a + close + b
        a = word[:r[0]]
        b = word[r[0]:]
        word = a + open + b
    return word


def compare(word1, word2):
    s = difflib.SequenceMatcher(None, word1, word2)
    blocks = s.get_matching_blocks()
    ranges = get_diff_ranges(blocks, 0)
    word1 = mark_up(word1,'<b>', '</b>', ranges )
    ranges = get_diff_ranges(blocks, 1)
    word2 = mark_up(word2,'<b>', '</b>', ranges )
    return word1, word2