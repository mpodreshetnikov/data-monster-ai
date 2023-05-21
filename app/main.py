import logging
from configparser import ConfigParser
import os

from langchain import SQLDatabase
from langchain.chat_models import ChatOpenAI
from langchain.base_language import BaseLanguageModel
from sqlalchemy import URL

import modules.tg.main as tg
from modules.brain.main import Brain
from modules.data_access.main import Engine


__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))


def main():
    config = ConfigParser()
    config.read(os.path.join(__location__, "settings.ini"))

    __configure_logger__(config)
    engine = __configure_engine(config)

    brain = __configure_brain__(config)
    brain.engine = engine

    run_in_console = config.getboolean(
        "debug", "run_in_console", fallback=False)
    if run_in_console:
        __run_bot_in_console_and_block_thread__(brain)

    tg_bot_token = config.get("tg", "bot_token")
    tg_users_whitelist = config.get("tg", "whitelist").split(",")
    tg.run_bot_and_block_thread(config, brain, engine)


def __run_bot_in_console_and_block_thread__(brain: Brain):
    while True:
        question = str(input("Задай вопрос: "))
        brain.answer(question)

def __run_bot_and_block_thread__(config: ConfigParser, brain: Brain, engine:Engine):
    tg_bot_token = config.get("tg", "bot_token")
    tg_users_whitelist = config.get("tg", "whitelist").split(",")
    tg_web_app_storage_base_link = config.get("tg", "web_app_storage_base_link")
    tg.run_bot_and_block_thread(tg_bot_token, brain, engine, tg_users_whitelist, tg_web_app_storage_base_link)

def __configure_brain__(config: ConfigParser) -> Brain:
    verbose = config.getboolean("debug", "verbose", fallback=False)
    db = __configure_db__(config)
    llm = __configure_llm__(config)
    brain = Brain(
        db=db,
        llm=llm,
        db_hints_doc_path=config.get("hints", "db_hints_doc_path"),
        prompt_log_path=config.get("debug", "prompt_log_path"),
        sql_query_examples_path=config.get("hints", "sql_query_examples_path"),
        sql_query_hints_limit=config.getint(
            "hints", "query_hints_limit", fallback=0),
        verbose=verbose,
    )
    return brain


def __configure_llm__(config: ConfigParser) -> BaseLanguageModel:
    verbose = config.getboolean("debug", "verbose", fallback=False)
    openai_api_key = config.get("openai", "api_key")
    temperature = config.getfloat("openai", "temperature", fallback=0.7)
    os.environ["OPENAI_API_KEY"] = openai_api_key
    llm = ChatOpenAI(verbose=verbose, temperature=temperature)
    return llm


def __configure_db__(config: ConfigParser) -> SQLDatabase:
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
    db = SQLDatabase.from_uri(
        url, schema=schema, include_tables=include_tables)
    return db


def __configure_logger__(config: ConfigParser, log_filename: str = 'log.txt'):
    log_formatter = logging.Formatter(
        "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    root_logger = logging.getLogger()

    log_path = config.get("common", "log_path", fallback="logs")
    file_handler = logging.FileHandler(
        "{0}/{1}".format(log_path, log_filename), mode='w')
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    verbose = config.getboolean("debug", "verbose", fallback=False)
    if verbose:
        root_logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        root_logger.addHandler(console_handler)


def __configure_engine(config: ConfigParser) -> Engine:
    url = URL.create(
        drivername=config.get("engine", "drivername", fallback="sqlite"),
        username=config.get("engine", "username"),
        password=config.get("engine", "password"),
        database=config.get("engine", "database"),
    )
    return Engine(url)


if __name__ == "__main__":
    main()
