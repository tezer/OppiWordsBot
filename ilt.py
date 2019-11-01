import spaced_repetition as sr
import mysql_connect as db

import logging
logger = logging.getLogger('ilt')
# hdlr = logging.StreamHandler()
hdlr = logging.FileHandler('ilt.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)


task_transitions={0:2, 2:1}
task_names={0: 'word_recognition',
            2: 'say_word',
            1: 'write_word'}


def level_up(session):
    hid = session.get_current_hid()
    sr.update_item(hid, 1)
    logger.debug("{}, level up for {} from level {}".format(session.get_user_id(),
                 session.get_current_word()[0], session.get_current_mode()))
    if session.get_current_mode() not in task_transitions.keys():
        logger.warning("{}, WRONG level up for {} from level {}".format(session.get_user_id(),
                 session.get_current_word()[0], session.get_current_mode()))
        session.delete_current_word()
        return
    new_hid = sr.add_item((session.get_user_id(), session.active_lang()),
                          (session.get_current_word()[0],
                           session.get_current_definition()),
                          task_transitions[session.get_current_mode()])
    db.insert_word(session.get_user_id(), session.active_lang(),
                              session.get_current_word()[0],
                              session.get_current_definition(),
                              task_transitions[session.get_current_mode()],
                              new_hid)
    session.level_up_current_word(new_hid, task_transitions[session.get_current_mode()])
    session.delete_current_word()