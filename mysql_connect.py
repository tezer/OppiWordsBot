import mysql.connector
from mysql.connector import Error
import hashlib
conf = dict()


def fetchone(query, args):
    row = tuple()
    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor(buffered=True)
        cursor.execute(query, args)
        row = cursor.fetchone()
    except Error as e:
        print(e)

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
        print(e)
        res = False
    finally:
        cursor.close()
        conn.close()
        return res


def fetchall(query):
    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor(buffered=True)
        cursor.execute(query)
        rows = cursor.fetchall()
    except Error as e:
        print(e)

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
        print(e)

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
        print(error)

    finally:
        cursor.close()
        conn.close()


def insert_words(words):
    query = "INSERT INTO words(user, language, word, definition, mode, hid) " \
            "VALUES(%s,%s,%s,%s,%s,%s)"

    try:
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor()
        cursor.executemany(query, words)
        conn.commit()
    except Error as error:
        print(error)

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
        print(error)

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
        print(error)

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
        print(error)

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
        print(error)

    finally:
        cursor.close()
        conn.close()



def add_list(user, word_list, lang, list_name):
    data = list()
    for word in word_list:
        hid = hashlib.md5((word+lang+user+list_name).encode('utf-8')).hexdigest()
        args = (hid, list_name, user, lang, word )
        data.append(args)

    try:
        query = "INSERT INTO word_lists (hid, listname, user, LANGUAGE, word ) " \
                "VALUES(%s,%s,%s,%s,%s)"
        conn = mysql.connector.connect(host=conf['host'],
                                       database=conf['database'],
                                       user=conf['user'],
                                       password=conf['password'])
        cursor = conn.cursor()
        cursor.executemany(query, data)
        conn.commit()
    except Error as error:
        print(error)

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
        print(e)
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
        print(error)

    finally:
        cursor.close()
        conn.close()
    return None

def test(c):
    global conf
    conf = c


if __name__ == '__main__':
    # insert_word("test", "lang", "word", "definition", 0, "12345")
    # words=[
    #     ("test", "lang", "word0", "definition", 0, "012345"),
    #     ("test", "lang1", "word1", "definition", 0, "0123451"),
    #     ("test", "lang", "word1", "definition", 0, "0123452"),
    #     ("test", "lang", "word2", "definition", 0, "0123453"),
    #     ("test", "lang1", "word0", "definition", 0, "0123454")
    # ]
    # insert_words(words)
    print(fetchall("SELECT word, language FROM words WHERE user='76673167' AND mode=0 AND language='finnish'"))
    # rows = fetchall("SELECT word, definition, mode FROM words WHERE user='test' AND hid='12345'")
    # print(rows)
    # fetchmany("SELECT * FROM words", 5)

