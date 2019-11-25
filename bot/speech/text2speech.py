"""Synthesizes speech from the input string of text or ssml.

Note: ssml must be well-formed according to:
    https://www.w3.org/TR/speech-synthesis/
"""
import io
import os
from expiringdict import ExpiringDict
from loguru import logger
from google.cloud.texttospeech_v1.proto.cloud_tts_pb2 import SynthesizeSpeechResponse

import settings
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]= settings.google_env
from google.cloud import texttospeech

MEM_CACHE = ExpiringDict(max_len=100, max_age_seconds=1000)

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
         'japanese': 'ja-JP'
         }
configs = dict()

# Select the type of audio file you want returned
audio_config = texttospeech.types.AudioConfig(
    audio_encoding=texttospeech.enums.AudioEncoding.MP3,
speaking_rate=0.75)


# Instantiates a client
client = texttospeech.TextToSpeechClient()

def get_lang_config(lang):
    if lang in configs.keys():
        return configs[lang]
    else:
        # Build the voice request, select the language code ("en-US") and the ssml
        # voice gender ("neutral")
        voice = texttospeech.types.VoiceSelectionParams(
            language_code=CODES[lang],
            ssml_gender=texttospeech.enums.SsmlVoiceGender.NEUTRAL)
        configs[lang] = voice
        return voice


def get_voice(word, lang):
    if word + '_' + lang in MEM_CACHE.keys():
        logger.debug("Got cached file for " + word + '_' + lang)
        return io.BytesIO(MEM_CACHE[word + '_' + lang])
    # Set the text input to be synthesized
    synthesis_input = texttospeech.types.SynthesisInput(text=word)
    # Perform the text-to-speech request on the text input with the selected
    # voice parameters and audio file type
    voice = get_lang_config(lang)
    r = client.synthesize_speech(synthesis_input, voice, audio_config)
    result = io.BytesIO(r.audio_content)
    MEM_CACHE[word + '_' + lang] = r.audio_content
    return result
#
# # The response's audio_content is binary.
# with open('output.mp3', 'wb') as out:
#     # Write the response to the output file.
#     out.write(response.audio_content)
#     print('Audio content written to file "output.mp3"')