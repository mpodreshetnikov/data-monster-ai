from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.callbacks import get_openai_callback
from sqlalchemy.engine import URL

import os
import time

is_debug = True
url = URL.create(
    "postgresql",
    username="gpt_bi_user",
    password="uzH#Q%N9YvM3f!",  
    host="62.109.28.9",
    port="2401",
    database="dwh_uas",
)
schema = "dwh_uas"
openai_api_key = "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"

os.environ["OPENAI_API_KEY"] = openai_api_key

db = SQLDatabase.from_uri(url, schema=schema)
llm = ChatOpenAI(verbose=is_debug)
toolkit = SQLDatabaseToolkit(db=db, llm=llm)

agent_executor = create_sql_agent(
    llm=ChatOpenAI(verbose=is_debug),
    toolkit=toolkit,
    verbose=is_debug,
)

#while True:
question = str(input())
with get_openai_callback() as cb:
    start = time.time()
    response = agent_executor.run(question)
    end  = time.time()
    print(f"Response: {response}")
    print(f"Time: {end-start}")
    print(f"Total Tokens: {cb.total_tokens}")
    print(f"Prompt Tokens: {cb.prompt_tokens}")
    print(f"Completion Tokens: {cb.completion_tokens}")
    print(f"Total Cost (USD): ${cb.total_cost}")

