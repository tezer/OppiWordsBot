# coding: utf-8

import requests
import requests.exceptions
import settings

class YandexTranslateException(Exception):
  """
  Default YandexTranslate exception
  """
  error_codes = {
    401: "ERR_KEY_INVALID",
    402: "ERR_KEY_BLOCKED",
    403: "ERR_DAILY_REQ_LIMIT_EXCEEDED",
    404: "ERR_DAILY_CHAR_LIMIT_EXCEEDED",
    413: "ERR_TEXT_TOO_LONG",
    422: "ERR_UNPROCESSABLE_TEXT",
    501: "ERR_LANG_NOT_SUPPORTED",
    503: "ERR_SERVICE_NOT_AVAIBLE",
  }

  def __init__(self, status_code, *args, **kwargs):
    message = self.error_codes.get(status_code)
    super(YandexTranslateException, self).__init__(message, *args, **kwargs)


class YandexTranslate(object):
  api_url = "https://translate.yandex.net/api/{version}/tr.json/{endpoint}"
  api_version = "v1.5"
  api_endpoints = {
    "langs": "getLangs",
    "detect": "detect",
    "translate": "translate",
  }

  def __init__(self, key=None):
    if not key:
      raise YandexTranslateException(401)
    self.api_key = key

  def url(self, endpoint):
    return self.api_url.format(version=self.api_version,
                               endpoint=self.api_endpoints[endpoint])

  @property
  def directions(self, proxies=None):
    try:
      response = requests.get(self.url("langs"), params={"key": self.api_key}, proxies=proxies)
    except requests.exceptions.ConnectionError:
      raise YandexTranslateException(self.error_codes[503])
    else:
      response = response.json()
    status_code = response.get("code", 200)
    if status_code != 200:
      raise YandexTranslateException(status_code)
    return response.get("dirs")

  @property
  def langs(self):
    return set(x.split("-")[0] for x in self.directions)

  def detect(self, text, proxies=None, format="plain"):
    data = {
      "text": text,
      "format": format,
      "key": self.api_key,
    }
    try:
      response = requests.post(self.url("detect"), data=data, proxies=proxies)
    except ConnectionError:
      raise YandexTranslateException(self.error_codes[503])
    except ValueError:
      raise YandexTranslateException(response)
    else:
      response = response.json()
    language = response.get("lang", None)
    status_code = response.get("code", 200)
    if status_code != 200:
      raise YandexTranslateException(status_code)
    elif not language:
      raise YandexTranslateException(501)
    return language

  def translate(self, text, lang, proxies=None, format="plain"):
    data = {
      "text": text,
      "format": format,
      "lang": lang,
      "key": self.api_key
    }
    try:
      response = requests.post(self.url("translate"), data=data, proxies=proxies)
    except ConnectionError:
      raise YandexTranslateException(503)
    else:
      response = response.json()
    status_code = response.get("code", 200)
    if status_code != 200:
      raise YandexTranslateException(status_code)
    return response

if __name__ == "__main__":
    tr = YandexTranslate(settings.ya_trans)
    print(tr.translate("Miksi englannin ääntäminen ja kirjoitusasu eroavat "
                       "toisistaan niin paljon? ￼; Joonas Vakkilainen, FM"
                       " suomen kielestä, erikoistunut fonetiikkaan; "
                       "Päivitetty 5. lokakuuta; "
                       "Yleisesti ottaen kirjoittaminen on yritys vangita "
                       "puhetta visuaaliseen muotoon.", lang='ru'))