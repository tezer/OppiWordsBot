import settings
from polyglot.text import Word

api_url = settings.w2v_api

import mysql_connect
import settings

mysql_connect.conf = settings.db_conf['prod']
N_LAST = 3

CODES = {
    'finnish': 'fi',
    'german': 'de',
    'english': 'en'
}

QUERY = 'SELECT w.word, s.last_date ' \
        'FROM spaced_repetition s ' \
        'INNER JOIN words w ON w.hid = s.hid ' \
        'WHERE w.user=%s ' \
        'AND w.language=\'{}\'' \
        'AND last_date IS NOT NULL ' \
        'ORDER BY last_date DESC;'
# select word from words where language='english' and user='444209921';

def get_user_words(user_id, lang):
    result = set()
    words = mysql_connect.fetchall(QUERY.format(lang), (user_id,))
    words = words[:N_LAST]
    for w in words:
        result.add(w[0])
    return result


def get_sems(word, lang):
    print(word)
    w = Word(word.lower(), language=CODES[lang.lower()])
    return w.neighbors


def get_list(user_id, lang):
    result = list()
    words = get_user_words(user_id, lang)
    words = [w.lower() for w in words]
    for w in words:
        sems = get_sems(w, lang)
        if sems is None:
            continue
        for s in sems:
            if s in words:
                continue
            result.append(s)
    return result[:20]

if __name__ == '__main__':
    words = get_list(0000)
    print(words)

