#Rename this file to "settings.py"
#Change data here to your actual settings
#Never upload your settings file to this repository

bot_token = {'dev': 'token for your development bot (Optional)',
             'prod': 'token for your bot'}

db_conf = {'dev': {
            "host": 'your db host',
              "database":'your db name',
              "user": 'db username',
              "password": 'db pass'},
           'prod': {
            "host": 'localhost',
              "database":'db name',
              "user": 'db username',
              "password": 'db pass'
           }}

admin=0000000 #You Telegram id
