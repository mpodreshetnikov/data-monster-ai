from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.callbacks import get_openai_callback
from langchain.agents.mrkl.output_parser import OutputParserException
from sqlalchemy.engine import URL

import os

from db_data_interaction.toolkit import DbDataInteractionToolkit
from prompts.agent_prompts import SQL_PREFIX, SQL_SUFFIX
from monitoring.callback import DefaultCallbackHandler

from utils.color import BOLD, END


is_debug = True
url = URL.create(
    "postgresql",
    username="gpt_bi_user",
    password="L4swy64n9fJkNt",  
    host="62.109.28.9",
    port="2401",
    database="dwh_uas2",
)
schema = "dwh_uas"
openai_api_key = "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"
tables_to_use = ["uas_cash_session_doc", "uas_cash_cheque", "uas_cash_cheque_item", "uas_cash_cheque_sum", "uas_data_med_nomenclature", "uas_data_user"]

os.environ["OPENAI_API_KEY"] = openai_api_key

db = SQLDatabase.from_uri(url, schema=schema, include_tables=tables_to_use)
toolkit = DbDataInteractionToolkit(
    db=db, llm=ChatOpenAI(verbose=is_debug), embeddings=OpenAIEmbeddings(),
    db_hints_doc_path="v2/test_scripts/db_hints.txt", sql_query_examples_path = "v2/test_scripts/sql_query_examples.yaml")
toolkit.build()


while True:
    print("Задай вопрос: ")
    question = str(input())
    with get_openai_callback() as cb:
        # Получаем подсказку для базы данных
        db_hint = toolkit.get_db_hint(question)

        # Получаем подсказки для запроса
        query_hints = toolkit.get_query_hints(question, 2)

        # Формируем строку с подсказками для вывода
        query_hints_str = ''.join([f"{BOLD}Question:{END} {hint.question}\n{BOLD}Query:{END}\n{hint.query}" for hint in query_hints])

        # Получаем уникальные таблицы из подсказок и получаем информацию о каждой таблице
        unique_tables = list(set(table for hint in query_hints for table in hint.tables))
        tables_info = ''.join(toolkit.get_table_info(table) for table in unique_tables)

        # Формируем строку с информацией о таблицах и примерами похожих запросов для вывода
        table_info_str = ('To answer the request, we have prepared a table/tables that you '
                          'that you need to use especially for you: {BOLD}{unique_tables}{END}.\n'
                          'Brief {BOLD}information about tables{END}: {tables_info}\n'
                          .format(unique_tables=unique_tables, tables_info=tables_info, BOLD = BOLD, END = END ))
        
        query_hints_str = 'Examples of similar queries:\n{query_hints_str}'.format(query_hints_str = query_hints_str)

        # Объединяем информацию о таблицах и примеры запросов в SQL_PREFIX
        output_str = f"{table_info_str} {query_hints_str}"
        SQL_PREFIX += output_str
        print(SQL_PREFIX)   
        try:
            agent_executor = create_sql_agent(
                llm=ChatOpenAI(verbose=is_debug),
                toolkit=toolkit,
                verbose=is_debug,
                prefix=SQL_PREFIX,
                suffix=SQL_SUFFIX,
            )
            response = agent_executor.run(question, callbacks=[DefaultCallbackHandler()])
        except OutputParserException as e:
            print(f"Не удается распознать результат работы ИИ: {e}")
            continue
        print(f"Response: {response}")
        print(cb)

