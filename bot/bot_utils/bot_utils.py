import json
import re
from wiktionaryparser import WiktionaryParser
from aiogram import types
from aiogram.utils.callback_data import CallbackData
from expiringdict import ExpiringDict
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


def get_definitions(language, user_lang, word):
    if language + '_' + user_lang + '_' + word in MEM_CACHE.keys():
        logger.debug("Reading translations from cache for " + language + '_' + user_lang + '_' + word)
        return MEM_CACHE[language + '_' + user_lang + '_' + word]
    result = list()
    if user_lang is None:
        user_lang = 'english'
    if user_lang in CODES.keys():
        try:
            response = ya_dict.lookup(word, CODES[language], CODES[user_lang])
            result = to_list(json.loads(response))

        except Exception as e:
            logger.warning("Yandex dictionary exception: " + str(e))
        if len(result) > 0:
            return result

    try:
        w = parser.fetch(word.lower(), language=language)
    except Exception as e:
        logger.warning("Wiktionary exception: " + str(e))
        MEM_CACHE[language + '_' + user_lang + '_' + word] = result
        return result
    if len(w) > 0:
        result = process_wiktionary(w)
        if len(result) > 0:
            return result
        elif len(word) <= 500 :
            try:
                tr = translate_client.translate(
                    word,
                    target_language=CODES[user_lang])
                result.append(tr['translatedText'])
            except Exception as e:
                print(e)
    MEM_CACHE[language + '_' + user_lang + '_' + word] = result
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