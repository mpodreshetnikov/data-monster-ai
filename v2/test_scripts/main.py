import os, configparser

from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.callbacks import get_openai_callback
from langchain.agents.mrkl.output_parser import OutputParserException
from sqlalchemy.engine import URL

from db_data_interaction.toolkit import DbDataInteractionToolkit
from prompts.agent_prompts import SQL_PREFIX, SQL_SUFFIX, get_formatted_hints
from monitoring.callback import DefaultCallbackHandler

from parsers.custom_output_parser import CustomOutputParserWithCallbackHandling, LastPromptSaverCallbackHandler


config = configparser.ConfigParser()
config.read("v2/test_scripts/settings.ini")


is_debug = config.getboolean("debug", "is_debug", fallback=False)
if is_debug:
    prompt_log_path = config.get("debug", "prompt_log_path")

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
llm = ChatOpenAI(verbose=is_debug)

db_hints_doc_path = config.get("hints", "db_hints_doc_path")
sql_query_examples_path = config.get("hints", "sql_query_examples_path")
query_hints_limit = config.getint("hints", "query_hints_limit", fallback=0)

toolkit = DbDataInteractionToolkit(
    db=db, llm=llm, embeddings=OpenAIEmbeddings(),
    db_hints_doc_path=db_hints_doc_path, sql_query_examples_path=sql_query_examples_path)
toolkit.build()


while True:
    print("Задай вопрос: ")
    question = str(input())
    with get_openai_callback() as cb:
        last_prompt_saver = LastPromptSaverCallbackHandler()
        output_parser = CustomOutputParserWithCallbackHandling(
            retrying_llm=llm,
            is_debug=is_debug,
            last_prompt_saver_callback_handler=last_prompt_saver)
        hints_str = get_formatted_hints(toolkit, question, query_hints_limit)
        agent_suffix = f"{hints_str}\n{SQL_SUFFIX}"
        try:
            agent_executor = create_sql_agent(
                llm=llm,
                toolkit=toolkit,
                verbose=is_debug,
                prefix=SQL_PREFIX,
                suffix=agent_suffix,
                output_parser=output_parser,
                agent_executor_kwargs={
                    # "handle_parsing_errors": True,
                },
            )
            response = agent_executor.run(question,
                                          callbacks=[
                                              DefaultCallbackHandler(log_path=prompt_log_path),
                                              last_prompt_saver,
                                            ])
        except OutputParserException as e:
            print(f"Не удается распознать результат работы ИИ: {e}")
            continue
        print(f"Response: {response}")
        print(cb)