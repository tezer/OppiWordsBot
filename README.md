# OppiWordsBot
A Telegram bot for learning languages

To run it you need Python 3.7 and:

1. register your own bot ad BotFather
2. set a MySQL database as follows:
mysql> describe spaced_repetition;

| Field      | Type         | Null | Key | Default           | Extra |
|------------|--------------|------|-----|-------------------|-------|
| hid        | varchar(255) | NO   | PRI | NULL              |       |
| model      | varchar(255) | YES  |     | NULL              |       |
| last_date  | varchar(255) | YES  |     | NULL              |       |
| created_at | timestamp    | NO   |     | CURRENT_TIMESTAMP |       |
| user       | varchar(255) | YES  |     | NULL              |       |
| language   | varchar(255) | YES  |     | NULL              |       |


mysql> describe users;

| Field         | Type         | Null | Key | Default           | Extra |
|---------------|--------------|------|-----|-------------------|-------|
| user_id       | varchar(255) | NO   | PRI | NULL              |       |
| first_name    | varchar(255) | YES  |     | NULL              |       |
| last_name     | varchar(255) | YES  |     | NULL              |       |
| language_code | varchar(255) | YES  |     | NULL              |       |
| created_at    | timestamp    | NO   |     | CURRENT_TIMESTAMP |       |
| blocked       | tinyint(1)   | YES  |     | 0                 |                             |
| lastUpdated   | timestamp    | NO   |     | CURRENT_TIMESTAMP | on update CURRENT_TIMESTAMP |

mysql> describe word_lists;

| Field    | Type         | Null | Key | Default | Extra |
|----------|--------------|------|-----|---------|-------|
| HID      | char(32)     | NO   | PRI | NULL    |       |
| LISTNAME | varchar(255) | NO   |     | NULL    |       |
| USER     | varchar(20)  | NO   |     | NULL    |       |
| language | varchar(20)  | YES  |     | NULL    |       |
| word     | varchar(255) | YES  |     | NULL    |       |



mysql> describe words;

| Field      | Type         | Null | Key | Default | Extra |
|------------|--------------|------|-----|---------|-------|
| word       | tinytext     | YES  |     | NULL    |       |
| definition | tinytext     | YES  |     | NULL    |       |
| mode       | tinyint(4)   | YES  |     | NULL    |       |
| hid        | varchar(255) | NO   | PRI | NULL    |       |
| user       | varchar(255) | YES  |     | NULL    |       |
| language   | varchar(255) | YES  |     | NULL    |       |
| listname   | varchar(255) | YES  |     | NULL    |       |

3. Store your credentials in settings.py

4. run it with in dev configuration: _python3.7 dev_ 
or in prod configuration _python3.7 prod_
