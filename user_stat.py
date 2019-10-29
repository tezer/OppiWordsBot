import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import spaced_repetition


oneHour = timedelta(hours=1)

conf = dict()

messages = {"no_words_added": "Looks like you haven't added words to learn yet? Try /setlanguage and then /addwords to add a few words.",
            "has_words_to_learn": "You have {} words to learn. Use /learn command to start learning them.",
            "all": "Hi!\nTry new SmartList for English language learners with /wordlist command."
                   "\nIf you have ideas to share, questions or suggestions, you can join <b>OppiWordsBotGroup</b> (https://t.me/OppiWords) to discuss . \n"
}



def get_user_last_activity(user=None):
    if user is None:
        print("ERROR, need user_id")
        return
    else:
        query = "SELECT last_date FROM spaced_repetition WHERE user='" + user + "'"

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


def is_within_time(period_in_hrs, times):
    for t in times:
        t = t[0]
        if t is None:
            continue
        lastTest = datetime.strptime(t, "%Y-%m-%dT%H:%M:%S.%f")
        time_passed = (datetime.now() - lastTest) / oneHour
        if time_passed < period_in_hrs:
            return True
    return False


def number_of_words_to_train(user):
    words = spaced_repetition.get_items_to_learn((user, None))
    return len(words)

def get_user_message(period):
    query = "SELECT user_id from users where blocked = 0"

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
        result = dict()
        for row in rows:
            user = row[0]
            times = get_user_last_activity(user)
            if is_within_time(period, times):
                continue
            n = number_of_words_to_train(user)
            result[user] = messages['all']
            if n == 0:
                result[user] += messages["no_words_added"]
            else:
                result[user] += messages["has_words_to_learn"].format(n)
        return result



if __name__ == '__main__':
    import settings
    conf = settings.db_conf['dev']
    import mysql_connect
    mysql_connect.test(conf)
    print(get_user_message(24))
