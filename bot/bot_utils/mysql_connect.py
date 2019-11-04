import calendar

import mysql.connector
from mysql.connector import Error
import hashlib
import datetime

from bot.app import core

from loguru import logger

conf = core.db_conf
logger.info(conf)

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

    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor(buffered=True)

        for hid in hids:
            query = "SELECT word, definition, mode, hid FROM words WHERE user=%s AND hid=%s"
            cursor.execute(query, (user_id, hid))
            row = cursor.fetchone()
            if row is not None:
                result.append(row)

    except Error as e:
        print("fetch_by_hids: ", e)

    finally:
        cursor.close()
        conn.close()
        return result


def delete_by_hid(hid):
    query = "DELETE FROM words WHERE hid = %s"
    args = (hid,)
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
        print('delete_by_hid', e)
        res = False
    finally:
        cursor.close()
        conn.close()
        return res


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


def insert_word(user, language, word, definition, mode, hid):
    query = "INSERT INTO words(user, language, word, definition, mode, hid) " \
            "VALUES(%s,%s,%s,%s,%s,%s)"
    args = (user, language, word, definition, mode, hid)

    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor(buffered=True)
        cursor.execute(query, args)

        conn.commit()
    except Error as error:
        print('insert_word', error)
        logger.error("{} received error message {}".format(user, error))
    finally:
        cursor.close()
        conn.close()


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


def unblock_user(user_id):
    query = "UPDATE users SET blocked = 0 WHERE user_id = %s"
    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor()
        cursor.execute(query, (user_id, ))
        conn.commit()
    except Error as error:
        print('unblock_user', error)
        logger.error("{} received error message {}".format(user_id, error))
    finally:
        cursor.close()
        conn.close()


def check_exists(user_id):
    res = False

    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor(buffered=True)

        query = "SELECT blocked FROM users WHERE user_id=%s"
        cursor.execute(query, (user_id, ))
        result = cursor.fetchone()

    except Error as e:
        print("check_exists: ", e)
        logger.error("{} received error message {}".format(user_id, e))
    finally:
        cursor.close()
        conn.close()
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

    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor()
        cursor.execute(query, args)
        conn.commit()
    except Error as error:
        print('update_user', error)
        logger.error("{} received error message {}".format(user_id, error))
    finally:
        cursor.close()
        conn.close()


def add_sr_item(hid, defaultModel, lastTime, user, language):
    query = "INSERT INTO spaced_repetition (hid, model, last_date, user, language) " \
            "VALUES(%s,%s,%s,%s,%s)"
    args = (hid, defaultModel, lastTime, user, language)

    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor()
        cursor.execute(query, args)
        conn.commit()
    except Error as error:
        logger.error("{} received error message {}".format(user, error))
        print('add_sr_item', error)

    finally:
        cursor.close()
        conn.close()


def update_sr_item(hid, model, lastTime):
    query = "UPDATE spaced_repetition SET model = %s, last_date = %s WHERE hid = %s"
    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor()
        cursor.execute(query, (model, lastTime, hid))
        conn.commit()
    except Error as error:
        print('update_sr_item', error)
        logger.error("{} received error message {}".format(hid, error))
    finally:
        cursor.close()
        conn.close()



def add_list(user, word_list, lang, list_name):
    data = list()
    logger.debug("Adding {} words to list_name {} for user {}"
                 .format(len(word_list), list_name, user))
    for word in word_list:
        hid = hashlib.md5((word+lang+user+list_name).encode('utf-8')).hexdigest()
        args = (hid, list_name, user, lang, word )
        data.append(args)

    try:
        query = "INSERT IGNORE INTO word_lists (hid, listname, user, LANGUAGE, word ) " \
                "VALUES(%s,%s,%s,%s,%s)"
        # query = "INSERT INTO word_lists (hid, listname, user, LANGUAGE, word ) " \
        #         "VALUES(%s,%s,%s,%s,%s)"
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
    result = list()

    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor(buffered=True)

        query = "SELECT listname, hid, word FROM word_lists WHERE user=%s AND language=%s AND listname=%s"
        cursor.execute(query, (user_id, language, list_name))
        result = cursor.fetchall()

    except Error as e:
        print("fetch_word_list: ", e)
        logger.error("{} received error message {}".format(user_id, e))
    finally:
        cursor.close()
        conn.close()
        return result



def delete_from_list(hid):
    query = "DELETE FROM word_lists WHERE hid = %s"
    args = (hid,)
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
        print('delete_from_list', e)
        logger.error("{} received error message {}".format(hid, e))
        res = False
    finally:
        cursor.close()
        conn.close()
        return res



def lists_to_add(user, lang):
    result = list()

    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor(buffered=True)

        query = "SELECT listname FROM word_lists WHERE user=%s AND language=%s"
        cursor.execute(query, (user, lang))
        result = cursor.fetchall()

    except Error as e:
        print("lists_to_add: ", e)
        logger.error("{} received error message {}".format(user, e))

    finally:
        cursor.close()
        conn.close()
        return result


def update_blocked(user_id):
    query = "UPDATE users SET blocked = 1 WHERE user_id = %s"
    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor()
        cursor.execute(query, (user_id,))
        conn.commit()
    except Error as error:
        print('update_blocked', error)
        logger.error("{} received error message {}".format(user_id, error))
    finally:
        cursor.close()
        conn.close()
    return None

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year,month)[1])
    return datetime.date(year, month, day)


def set_premium(user, number_of_month):
    # TODO check the input
    n = int(number_of_month)
    # TODO get the start_date from DB if current subscription is still on
    start_date = datetime.date.today()
    end_date = add_months(start_date, n)
    print(user, start_date, end_date)
    return end_date

def check_subscribed(user):
    query = "SELECT to_date FROM subscribed WHERE user=%s"
    date = fetchone(query, user)
    if len(date) == 0:
        return False
    else:
        d = date[0]
        f = '%Y-%m-%d'
        d = date.strptime(d, f)
        return date.now() <= d


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

