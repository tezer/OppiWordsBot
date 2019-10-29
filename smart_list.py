import json

import wordfreq
import requests
import requests.exceptions
import settings

api_url = settings.w2v_api

import mysql_connect
import settings

mysql_connect.conf = settings.db_conf['prod']
N_LAST = 5

# QUERY = 'SELECT w.word, s.last_date ' \
QUERY = 'SELECT w.word, s.last_date ' \
        'FROM spaced_repetition s ' \
        'INNER JOIN words w ON w.hid = s.hid ' \
        'WHERE w.user=%s ' \
        'AND w.language=\'english\'' \
        'AND last_date IS NOT NULL ' \
        'ORDER BY last_date DESC;'
# select word from words where language='english' and user='444209921';

def get_user_words(user_id):
    result = set()
    words = mysql_connect.fetchall(QUERY, (user_id,))
    words = words[:N_LAST]
    for w in words:
        result.add(w[0])
    return result


def get_sems(word):
    try:
        response = requests.get(
            api_url + '?' + word)
    except requests.exceptions.ConnectionError as e:
        print(e)
    data = json.loads(response.text)
    if len(data) == 0:
        return
    return data[word]['sems']


def get_list(user_id):
    result = list()
    words = get_user_words(user_id)
    words = [w.lower() for w in words]
    for w in words:
        sems = get_sems(w)
        if sems is None:
            continue
        for s in sems:
            if s in words:
                continue
            result.append(s)
    return result

if __name__ == '__main__':
    words = get_list(76673167)
    print(words)
    # print(len(words))
    # n = 0
    # for w in words.items():
    #     z = wordfreq.zipf_frequency(w[0], lang='en')
    #     print('=' * 20, '\n',w, z, w[1], '\n')
    #     sems = get_sems(w[0])
    #     if sems is None:
    #         continue
    #     n += len(sems)
    #     for s in sems:
    #         print(s, wordfreq.zipf_frequency(s, lang='en'))
    # print(n)
