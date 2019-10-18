# https://github.com/LuminosoInsight/wordfreq

from wordfreq import (
    zipf_frequency,
    top_n_list, random_words, tokenize
)

CODES = {'arabic': 'ar',
'bengali': 'bn',
'bosnian': 'bs',
'bulgarian': 'bg',
'catalan': 'ca',
'chinese': 'zh',
'croatian': 'hr',
'czech': 'cs',
'danish': 'da',
'dutch': 'nl',
'english': 'en',
'finnish': 'fi',
'french': 'fr',
'german': 'de',
'greek': 'el',
'hebrew': 'he',
'hindi': 'hi',
'hungarian': 'hu',
'indonesian': 'id',
'italian': 'it',
'japanese': 'ja',
'korean': 'ko',
'latvian': 'lv',
'macedonian': 'mk',
'malay': 'ms',
'norwegian': 'nb',
'persian': 'fa',
'polish': 'pl',
'portuguese': 'pt',
'romanian': 'ro',
'russian': 'ru',
'serbian': 'sr',
'spanish': 'es',
'swedish': 'sv',
'turkish': 'tr',
'ukrainian': 'uk',
}

def language_supported(lang):
    return lang in CODES.keys()

def get_top_n(lang, start=0, end=100):
    if language_supported(lang):
        top_n = top_n_list(CODES[lang], end, wordlist='best')
        top_n = top_n[start: end]
        return top_n


def tokinzation(text, lang):
    return (tokenize(text, lang))


# print(get_top_n('finnish', start=10, end=20))