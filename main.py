import dbaccess, ai, answering
import psycopg2, configparser

# configure
config = configparser.ConfigParser()
config.read("settings.ini")

ai.set_openai_api_key(config["openai"]["ApiKey"])
dbaccess.db_conn = psycopg2.connect(
    host = config["db"]["Host"],
    dbname = config["db"]["Database"],
    user = config["db"]["User"],
    password = config["db"]["Password"],
    port = config["db"]["Port"]
)

# answering
question = "названия неархивных приемов пищи гис"
answer = answering.answer(question)
print(answer)

dbaccess.db_conn.close()



# do no_data message when cur.rowcount = 0

# учесть причины остановки генерации ответа
# simple requests
# graphic requests
# table requests
# скачивание эксель файла при необходимости
