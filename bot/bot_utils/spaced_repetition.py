import ebisu
from datetime import datetime, timedelta
import hashlib
import json
from bot.bot_utils import mysql_connect as db

oneHour = timedelta(hours=1)
defaultModel = (3., 3., 4.)  # alpha, beta, and half-life in hours


def add_item(user_language, word_meaning, mode):
    s = str(user_language[0]) + str(user_language[1]) \
        + str(word_meaning[0]) + str(word_meaning[1]) + str(mode)
    s = s.encode('utf-8')
    hid = hashlib.md5(s).hexdigest()
    db.add_sr_item(hid, json.dumps(defaultModel), None, user_language[0], user_language[1])
    return hid


def update_item(hid, result):
    time_passed = 0.1
    word = db.fetchone("SELECT model, last_date FROM spaced_repetition WHERE hid=%s", (hid,))
    if word[1] is not None:
        lastTest = datetime.strptime(word[1], "%Y-%m-%dT%H:%M:%S.%f")
        time_passed = (datetime.now() - lastTest) / oneHour
    model = tuple(json.loads(word[0]))
    recall = ebisu.predictRecall(model, time_passed, exact=True)
    print(str(hid), str(recall))
    new_model = ebisu.updateRecall(model, result, time_passed)
    print(hid, result)
    print(model)
    print(new_model)
    db.update_sr_item(hid, json.dumps(new_model), datetime.now().isoformat())
    return True


def get_items_to_learn(user_language, upper_recall_limit=0.5, n=-1):
    result = list()
    now = datetime.now()
    tmp = dict()
    if (user_language[1] is not None):
        words = db.fetchall("SELECT hid, model, last_date FROM spaced_repetition WHERE user=%s and language=%s",
                            (user_language[0], user_language[1]))
    else:
        words = db.fetchall("SELECT hid, model, last_date FROM spaced_repetition WHERE user=%s", (user_language[0],))
    for word in words:
        hid = word[0]
        model = tuple(json.loads(word[1]))
        lastTest = word[2]
        if lastTest is None:
            result.append(hid)
            continue
        lastTest = datetime.strptime(lastTest, "%Y-%m-%dT%H:%M:%S.%f")
        recall = ebisu.predictRecall(model, (now - lastTest) / oneHour, exact=True)
        if recall <= upper_recall_limit:
            tmp[hid] = recall
    recalls = list(tmp.values())
    recalls.sort()
    if n > 0:
        n = min(n, len(recalls))
    else:
        n = len(recalls)
    for r in recalls:
        for hid, recall in tmp.items():
            if len(result) >= n:
                break
            if recall == r:
                result.append(hid)
    return result
