import logging
from configparser import ConfigParser
import os

from langchain import SQLDatabase
from langchain.chat_models import ChatOpenAI
from langchain.base_language import BaseLanguageModel
from mypy_boto3_s3 import S3Client
from sqlalchemy import URL
import boto3

import modules.tg.main as tg
from modules.brain.main import Brain
from modules.data_access.main import InternalDB

from utils.multischema_sql_database import MultischemaSQLDatabase


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def main():
    config = ConfigParser()
    config.read(os.path.join(__location__, "settings.ini"))

    __configure_logger__(config)
    internal_db = __configure_engine__(config)

    brain = __configure_brain__(config)
    brain.internal_db = internal_db

    s3client = __configure_s3(config)

    run_in_console = config.getboolean(
        "debug", "run_in_console", fallback=False)
    if run_in_console:
        __run_bot_in_console_and_block_thread__(brain)

    
    __run_bot_and_block_thread__(config, brain, internal_db, s3client)


def __run_bot_in_console_and_block_thread__(brain: Brain):
    while True:
        question = str(input("Задай вопрос: "))
        brain.answer(question)


def __run_bot_and_block_thread__(config: ConfigParser, brain: Brain, internal_db: InternalDB, s3client: S3Client):
    tg_bot_token = config.get("tg", "bot_token")
    tg_users_whitelist = config.get("tg", "whitelist").split(",")
    statistic = config.get("common", "statistic")
    tg_web_app_storage_base_link = config.get("tg", "web_app_storage_base_link")
    tg.run_bot_and_block_thread(
        tg_bot_token, brain, internal_db, tg_users_whitelist, tg_web_app_storage_base_link, s3client, statistic)


def __configure_brain__(config: ConfigParser) -> Brain:
    verbose = config.getboolean("debug", "verbose", fallback=False)
    client_db = __configure_client_db__(config)
    llm = __configure_llm__(config)
    return Brain(
        db=client_db,
        llm=llm,
        db_hints_doc_path=config.get("hints", "db_hints_doc_path"),
        db_comments_override_path=config.get("hints", "db_comments_override_path"),
        prompt_log_path=config.get("debug", "prompt_log_path"),
        sql_query_examples_path=config.get("hints", "sql_query_examples_path"),
        sql_query_hints_limit=config.getint("hints", "query_hints_limit", fallback=0),
        verbose=verbose,
    )


def __configure_llm__(config: ConfigParser) -> BaseLanguageModel:
    verbose = config.getboolean("debug", "verbose", fallback=False)
    openai_api_key = config.get("openai", "api_key")
    temperature = config.getfloat("openai", "temperature", fallback=0.7)
    os.environ["OPENAI_API_KEY"] = openai_api_key
    return ChatOpenAI(verbose=verbose, temperature=temperature)


def __configure_client_db__(config: ConfigParser) -> SQLDatabase:
    url = URL.create(
        drivername=config.get("client_db", "drivername", fallback="postgresql"),
        username=config.get("client_db", "username"),
        password=config.get("client_db", "password"),
        host=config.get("client_db", "host"),
        port=config.getint("client_db", "port"),
        database=config.get("client_db", "database"),
    )
    schema = config.get("client_db", "schema")
    include_tables = config.get("client_db", "tables_to_use").split(",")
    return MultischemaSQLDatabase.from_uri(url, schema=schema, include_tables=include_tables)


def __configure_logger__(config: ConfigParser, log_filename: str = "log.txt"):
    log_formatter = logging.Formatter(
        "%(asctime)s [%(threadName)-12.12s] [%(levelname)-7.7s]  %(message)s"
    )
    root_logger = logging.getLogger()

    log_path = config.get("common", "log_path", fallback="logs")
    file_handler = logging.FileHandler(
        "{0}/{1}".format(log_path, log_filename), mode="w"
    )
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    if verbose := config.getboolean("debug", "verbose", fallback=False):
        root_logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        root_logger.addHandler(console_handler)


def __configure_engine__(config: ConfigParser) -> InternalDB:
    url = URL.create(
        drivername=config.get("internal_db", "drivername", fallback="sqlite"),
        database=config.get("internal_db", "database"),
    )
    return InternalDB(url)


def __configure_s3(config: ConfigParser):
    access_key = config.get("s3", "access_key")
    secret_key = config.get("s3", "secret_key")
    endpoint_url = config.get("s3", "endpoint_url")
    client = boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint_url
    )

    # test connection
    client.list_buckets()

    return client


if __name__ == "__main__":
    main()