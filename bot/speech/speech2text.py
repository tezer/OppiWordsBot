# Imports the Google Cloud client library

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types as gtypes
import urllib.request
import os
from loguru import logger

import settings
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]= settings.google_env


configs = dict()

CODES = {'czech': 'cs-CZ',
         'danish': 'da-DK',
         'dutch': 'nl-NL',
         'english': 'en-US',
         'finnish': 'fi-FI',
         'french': 'fr-FR',
         'german': 'de-DE',
         'greek': 'el-GR',
         'hungarian': 'hu-HU',
         'italian': 'it-IT',
         'latvian': 'lv-LV',
         'norwegian': 'nb-NO',
         'polish': 'pl-PL',
         'portuguese': 'pt-PT',
         'russian': 'ru-RU',
         'spanish': 'es-ES',
         'swedish': 'sv-SE',
         'turkish': 'tr-TR',
         'ukrainian': 'uk-UA',
         }

# Instantiates a client
client = speech.SpeechClient()



def get_lang_config(lang):
    if lang in configs.keys():
        return configs[lang]
    else:
        config = gtypes.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.OGG_OPUS,
            sample_rate_hertz=16000,
            language_code=CODES[lang])
        configs[lang] = config
        return config


def transcribe(url, lang):
    logger.debug("got url {} for language {}".format(url, lang))
    conf = get_lang_config(lang)
    response = urllib.request.urlopen(url)
    data = response.read()
    audio = gtypes.RecognitionAudio(content=data)
    response = client.recognize(conf, audio)
    results = response.results
    if len(results) == 0:
        return ""
    return results[0].alternatives[0].transcript



