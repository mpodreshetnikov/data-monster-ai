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

agent_executor = create_sql_agent(
    llm=ChatOpenAI(verbose=is_debug),
    toolkit=toolkit,
    verbose=is_debug,
    prefix=SQL_PREFIX,
    suffix=SQL_SUFFIX,
)

while True:
    print("Задай вопрос: ")
    question = str(input())
    with get_openai_callback() as cb:
        # prepare prompt preffix
        db_hint = toolkit.get_db_hint(question)
        query_hints = toolkit.get_query_hints(question, 2)
        query_hints_str = ', '.join([f"question: {d.question}, query: '{d.query}'" for d in query_hints])
        unique_tables = list(set(table for hint in query_hints for table in hint.tables))
        tables_info = ''.join(toolkit.tools[1]._run(table) for table in unique_tables)
        SQL_PREFIX += f'Для ответа на запрос специально для вас приготовили таблицу/таблицы, которыми необходимо пользоваться:{unique_tables}. Краткая информация о таблицах:{tables_info}. Примеры наболее похожих запросов {query_hints_str}'
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

