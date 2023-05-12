import os, configparser

from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.callbacks import get_openai_callback
from langchain.agents.mrkl.output_parser import OutputParserException
from sqlalchemy.engine import URL

from db_data_interaction.toolkit import DbDataInteractionToolkit
from prompts.agent_prompts import SQL_SUFFIX, get_formatted_prefix_with_additional_info
from monitoring.callback import DefaultCallbackHandler

from parsers.custom_output_parser import CustomOutputParser


config = configparser.ConfigParser()
config.read("v2/test_scripts/settings.ini")


is_debug = config.getboolean("modes", "is_debug", fallback=False)

url = URL.create(
    drivername=config.get("db", "drivername", fallback="postgresql"),
    username=config.get("db", "username"),
    password=config.get("db", "password"),  
    host=config.get("db", "host"),
    port=config.get("db", "port"),
    database=config.get("db", "database"),
)
schema = config.get("db", "schema")
include_tables = config.get("db", "tables_to_use").split(",")
db = SQLDatabase.from_uri(url, schema=schema, include_tables=include_tables)

openai_api_key = config.get("openai", "api_key")
os.environ["OPENAI_API_KEY"] = openai_api_key

db_hints_doc_path = config.get("paths", "db_hints_doc_path")
sql_query_examples_path = config.get("paths", "sql_query_examples_path")

toolkit = DbDataInteractionToolkit(
    db=db, llm=ChatOpenAI(verbose=is_debug), embeddings=OpenAIEmbeddings(),
    db_hints_doc_path=db_hints_doc_path, sql_query_examples_path=sql_query_examples_path)
toolkit.build()


while True:
    print("Задай вопрос: ")
    question = str(input())
    with get_openai_callback() as cb:
        agent_prefix = get_formatted_prefix_with_additional_info(toolkit, question, query_hints_limit=3)
        print(agent_prefix)
        try:
            agent_executor = create_sql_agent(
                llm=ChatOpenAI(verbose=is_debug),
                toolkit=toolkit,
                verbose=is_debug,
                prefix=agent_prefix,
                suffix=SQL_SUFFIX,
                output_parser = CustomOutputParser()
            )
            response = agent_executor.run(question, callbacks=[DefaultCallbackHandler()])
        except OutputParserException as e:
            print(f"Не удается распознать результат работы ИИ: {e}")
            continue
        print(f"Response: {response}")
        print(cb)