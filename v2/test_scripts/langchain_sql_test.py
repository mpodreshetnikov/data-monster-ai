from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.chat_models import ChatOpenAI
from langchain.callbacks import get_openai_callback
from langchain.agents.mrkl.output_parser import OutputParserException
from sqlalchemy.engine import URL

import os

from db_data_interaction.toolkit import DbDataInteractionToolkit
from prompts.agent_prompts import SQL_PREFIX, SQL_SUFFIX


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
llm = ChatOpenAI(verbose=is_debug)
toolkit = DbDataInteractionToolkit(db=db, llm=llm, db_doc_path="v2/test_scripts/db_doc.txt")

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
        try:
            response = agent_executor.run(question)
        except OutputParserException as e:
            print(f"Не удается распознать результат работы ИИ: {e}")
            continue
        print(f"Response: {response}")
        print(cb)

