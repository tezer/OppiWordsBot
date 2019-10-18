import re
from wiktionaryparser import WiktionaryParser
from aiogram import types
from aiogram.utils.callback_data import CallbackData
import logging
logger = logging.getLogger('utils')
# hdlr = logging.StreamHandler()
hdlr = logging.FileHandler('bot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)


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



def get_definitions(language, word):
    result = list()
    try:
        w = parser.fetch(word.lower(), language=language)
    except Exception as e:
        logger.warning("Wiktionary exception: " + str(e))
        return result
    if len(w) == 0:
        logger.debug("No data: " + str(w) + " : " + word)
        return result
    for definition in w[0]['definitions']:
        pos = definition['partOfSpeech']
        for d in definition['text'][1:]:
            result.append(d + " (" + pos + ")")
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


