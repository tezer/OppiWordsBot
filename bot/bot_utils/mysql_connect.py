import calendar

import mysql.connector
from mysql.connector import Error
import hashlib
import datetime

from bot.app import core

from loguru import logger

conf = core.db_conf



def insertone(query, args):
    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor()
        cursor.execute(query, args)
        conn.commit()
    except Error as error:
        logger.error("received error message {}".format(error))
        print('insertone', error)

    finally:
        cursor.close()
        conn.close()


def updateone(query, args):
    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor()
        cursor.execute(query, args)
        conn.commit()
    except Error as error:
        print('updateone', error)
        logger.error("{} received error message {}".format(query, error))
    finally:
        cursor.close()
        conn.close()
    return None


def fetchone(query, args):
    logger.info(conf)
    row = tuple()
    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'],
                                       port=conf['port'])
        cursor = conn.cursor(buffered=True)
        cursor.execute(query, args)
        row = cursor.fetchone()
    except Error as e:
        logger.error(e)
        print("fetchone", e)
    finally:
        cursor.close()
        conn.close()
        return row


def fetch_by_hids(user_id, hids):
    result = list()
    for hid in hids:
        query = "SELECT word, definition, mode, hid FROM words WHERE user=%s AND hid=%s"
        args = (user_id, hid)
        row = fetchone(query, args)
        if row is not None:
            result.append(row)
    return result


def deleteone(query, args):
    res = True
    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor()
        cursor.execute(query, args)
        conn.commit()
    except Error as e:
        print('deleteone', e)
        logger.error(e)
        res = False
    finally:
        cursor.close()
        conn.close()
        return res

def delete_by_hid(hid):
    query = "DELETE FROM words WHERE hid = %s"
    args = (hid,)
    res1 = deleteone(query, args)
    query = "DELETE FROM spaced_repetition WHERE hid = %s"
    res2 = deleteone(query, args)
    return res1 and res2


def fetchall(query, args):
    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'],
                                       port=conf['port'])
        cursor = conn.cursor(buffered=True)
        cursor.execute(query, args)
        rows = cursor.fetchall()
    except Error as e:
        print('fetchall', e)

    finally:
        cursor.close()
        conn.close()
        return rows


def iter_row(cursor, size=10):
    while True:
        rows = cursor.fetchmany(size)
        if not rows:
            break
        for row in rows:
            yield row


def fetchmany(query, n):
    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor()
        cursor.execute(query)
        for row in iter_row(cursor, size=n):
            print(row)

    except Error as e:
        print('fetchmany', e)

    finally:
        cursor.close()
        conn.close()

#WORDS =========================================================================
def insert_word(user, language, word, definition, mode, hid, listname=None, list_hid=None):
    query = "INSERT INTO words(user, language, word, definition, mode, hid, listname, list_hid) " \
            "VALUES(%s,%s,%s,%s,%s,%s, %s, %s)"
    args = (user, language, word, definition, mode, hid, listname, list_hid)

    insertone(query, args)


def insert_words(words):
    query = "INSERT INTO words(user, language, word, definition, mode, hid) " \
            "VALUES(%s,%s,%s,%s,%s,%s)"
    user = words[0][0]
    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor()
        cursor.executemany(query, words)
        conn.commit()
    except Error as error:
        print('insert_words', error)
        logger.error("{} received error message {}".format(user, error))
    finally:
        cursor.close()
        conn.close()


def add_sr_item(hid, defaultModel, lastTime, user, language):
    query = "INSERT INTO spaced_repetition (hid, model, last_date, user, language) " \
            "VALUES(%s,%s,%s,%s,%s)"
    args = (hid, defaultModel, lastTime, user, language)
    insertone(query, args)


def update_sr_item(hid, model, lastTime):
    query = "UPDATE spaced_repetition SET model = %s, last_date = %s WHERE hid = %s"
    args = (model, lastTime, hid)
    updateone(query, args)


def get_hid(word, lang, user, list_name):
    return hashlib.md5((word + lang + user + list_name).encode('utf-8')).hexdigest()

#LISTS =====================================================================================
def add_list(user, word_list, lang, list_name):
    data = list()
    logger.debug("Adding {} words to list_name {} for user {}"
                 .format(len(word_list), list_name, user))
    for word in word_list:
        hid = get_hid(word, lang, user,  list_name)
        args = (hid, list_name, user, lang, word)
        data.append(args)

    try:
        query = "INSERT IGNORE INTO word_lists (hid, listname, user, LANGUAGE, word ) " \
                "VALUES(%s,%s,%s,%s,%s)"

        logger.debug("{} data ready".format(user))
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor()
        cursor.executemany(query, data)
        conn.commit()
    except Error as error:
        print(error)
        logger.error("{} user got error while adding data to db {}".format(user, error))
    finally:
        cursor.close()
        conn.close()


def get_list(user_id, language, list_name):
    query = "SELECT listname, hid, word FROM word_lists WHERE user=%s AND language=%s AND listname=%s"
    args =  (user_id, language, list_name)
    result = fetchall(query, args)
    return result


def delete_from_list(hid):
    query = "DELETE FROM word_lists WHERE hid = %s"
    args = (hid,)
    return deleteone(query, args)


def lists_to_add(user, lang):
    query = "SELECT listname FROM word_lists WHERE user=%s AND language=%s"
    args = (user, lang)
    result = fetchall(query, args)
    return result



#USER MANAGEMENT =====================================================================

def update_blocked(user_id):
    query = "UPDATE users SET blocked = 1 WHERE user_id = %s"
    args = (user_id,)
    updateone(query, args)
    return None



def unblock_user(user_id):
    query = "UPDATE users SET blocked = 0 WHERE user_id = %s"
    args = (user_id,)
    updateone(query, args)


def check_exists(user_id):
    res = False
    query = "SELECT blocked FROM users WHERE user_id=%s"
    args = (user_id,)
    result = fetchone(query, args)
    if result is not None:
        res = True
        if result[0] == 1:
            unblock_user(user_id)
    return res


def update_user(user_id, first_name, last_name, language_code):
    exist = check_exists(user_id)
    if exist:
        return
    query = "INSERT INTO users(user_id, first_name, last_name, language_code) " \
            "VALUES(%s,%s,%s,%s)"
    args = (user_id, first_name, last_name, language_code)
    insertone(query, args)

# SUBSCRIPTION =====================================================================
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def get_subscription_dates(user):
    query = "SELECT start_date, end_date FROM subscribed WHERE user=%s"
    date = fetchone(query, (user,))
    if date is None or len(date) == 0:
        return None
    else:
        return date


def set_premium(user, number_of_month):
    try:
        n = int(number_of_month)
    except ValueError as  e:
        logger.error(e)
        return False
    start_date = datetime.date.today()
    if check_subscribed(user):
        dates = get_subscription_dates(user)
        end_date = add_months(dates[1], n)
        data = (start_date, end_date, user)
        query = 'UPDATE subscribed SET start_date = %s, end_date=%s WHERE user_id = %s'
        updateone(query, data)
    else:
        end_date = add_months(start_date, n)
        query = "INSERT INTO subscribed (user, start_date,  end_date) " \
                "VALUES(%s,%s,%s)"
        data = (user, start_date, end_date)
        insertone(query, data)

    logger.info("{} subscribed from {} to {}", user, start_date, end_date)
    return end_date


def check_subscribed(user):
    d = get_subscription_dates(user)
    if d is None:
        return False
    end_date = datetime.datetime.strptime(str(d[1]), "%Y-%m-%d")
    return datetime.date.today() <= end_date.date()

#TEXTS ============================================================
def add_text(language, text):
    hid = hashlib.md5(text.encode('utf-8')).hexdigest()

    query = "INSERT INTO texts (hid, language, text) " \
                "VALUES(%s,%s,%s)"
    args = (hid, language, text)
    insertone(query, args)
    return hid


def add_user_text(user, hid):

    query = "INSERT INTO user_texts (user, text_hid) " \
                "VALUES(%s,%s)"
    args = (user, hid)
    insertone(query, args)

def add_sentence(text, start, end, text_hid):
    hid = hashlib.md5((text).encode('utf-8')).hexdigest()
    query = "INSERT INTO sentences (hid, start, end, text_hid) " \
                "VALUES(%s, %s, %s, %s)"
    args = (hid, start, end, text_hid)
    insertone(query, args)
    return hid

def add_sentence_translation(translation, sent_hid, lang):
    hid = hashlib.md5((translation).encode('utf-8')).hexdigest()
    query = "INSERT INTO translations (hid, sent_hid, language, translation) " \
                "VALUES(%s, %s, %s, %s)"
    args = (hid, sent_hid, lang, translation)
    insertone(query, args)
    return hid

def add_text_word(word, sent_hid, lang, user,  list_name):
    logger.debug("{} {}", word, type(word))
    hid = get_hid(word, lang, str(user),  list_name)
    query = "INSERT INTO  text_words(hid, sent_hid) " \
                "VALUES(%s, %s)"
    args = (hid,sent_hid)
    insertone(query, args)
    query = "INSERT IGNORE INTO word_lists (hid, listname, user, LANGUAGE, word ) " \
                "VALUES(%s,%s,%s,%s,%s)"
    args = (hid, list_name, user, lang, word)
    insertone(query, args)

def get_context(list_hid):
    translation = ''
    context = ''
    query = 'SELECT sent_hid FROM text_words WHERE hid=%s'
    args = (list_hid, )
    sent_hid = fetchone(query, args)
    if sent_hid is None or len(sent_hid) == 0:
        return ''

    query = 'SELECT translation FROM translations WHERE sent_hid=%s';
    res = fetchone(query, sent_hid)
    if len(res) > 0:
        translation = res[0]

    query = 'SELECT start, end, text_hid FROM sentences WHERE hid=%s'
    start_end_text_hid = fetchone(query, sent_hid)

    query = 'SELECT text FROM texts WHERE hid=%s'
    args = (start_end_text_hid[2],)
    text = fetchone(query, args)[0]
    if text is not None and len(text) >= start_end_text_hid[1]:
        context = text[start_end_text_hid[0]:start_end_text_hid[1]]
    return translation, context


def test(c):
    global conf
    conf = c

# if __name__ == '__main__':
#     set_premium('000', '1')
# insert_word("test", "lang", "word", "definition", 0, "12345")
# words=[
#     ("test", "lang", "word0", "definition", 0, "012345"),
#     ("test", "lang1", "word1", "definition", 0, "0123451"),
#     ("test", "lang", "word1", "definition", 0, "0123452"),
#     ("test", "lang", "word2", "definition", 0, "0123453"),
#     ("test", "lang1", "word0", "definition", 0, "0123454")
# ]
# insert_words(words)
# print(fetchall("SELECT word, language FROM words WHERE user='76673167' AND mode=0 AND language='finnish'"))
# rows = fetchall("SELECT word, definition, mode FROM words WHERE user='test' AND hid='12345'")
# print(rows)
# fetchmany("SELECT * FROM words", 5)