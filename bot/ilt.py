from loguru import logger
from bot.bot_utils import spaced_repetition as sr, mysql_connect as db
from collections import OrderedDict

task_transitions = {0: 3, 3: 2, 2: 1, 1: 10, 10: 20}
tasks = OrderedDict()
tasks[0] = 'word_recognition'
tasks[3] = 'pronounce'
tasks[2] = 'say_word'
tasks[1] = 'type_in'
tasks[10] = 'unscramble'
tasks[20] = 'text_writing_up'


@logger.catch
def level_up(session):
    hid = session.get_current_hid()
    sr.update_item(hid, 1)
    logger.debug("{}, level up for {} from level {}".format(session.get_user_id(),
                                                            session.get_current_word()[0], session.get_current_mode()))
    if session.get_current_mode() not in task_transitions.keys():
        logger.warning("{}, WRONG level up for {} from level {}".format(session.get_user_id(),
                                                                        session.get_current_word()[0],
                                                                        session.get_current_mode()))
        session.delete_current_word()
        return
    new_hid = sr.add_item((session.get_user_id(), session.active_lang()),
                          (session.get_current_word()[0],
                           session.get_current_definition()),
                          task_transitions[session.get_current_mode()])
    db.level_up_word(hid, task_transitions[session.get_current_mode()], new_hid)
    session.level_up_current_word(new_hid, task_transitions[session.get_current_mode()])
    session.delete_current_word()


def sort_words(words):
    result = list()
    for i in tasks.keys():
        for word in words:
            if word[2] == i:
                result.append(word)
    return result
