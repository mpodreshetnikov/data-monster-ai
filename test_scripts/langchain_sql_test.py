from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.agents import AgentExecutor
from langchain.callbacks import get_openai_callback
from sqlalchemy import URL

import time

url = URL.create(
    "postgresql",
    username="gpt_bi_user",
    password="uzH#Q%N9YvM3f!",  
    host="62.109.28.9",
    port="2401",
    database="dwh_uas",
)

print(url)

openai_api_key = "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"

db = SQLDatabase.from_uri(url)
toolkit = SQLDatabaseToolkit(db=db)

agent_executor = create_sql_agent(
    llm=OpenAI(temperature=0, openai_api_key=openai_api_key),
    toolkit=toolkit,
    verbose=True
)

#while True:
question = str(input())
with get_openai_callback() as cb:
    start = time.time()
    response = agent_executor.run(question)
    end  = time.time()
    print(f"Time: {end-start}")
    print(f"Total Tokens: {cb.total_tokens}")
    print(f"Prompt Tokens: {cb.prompt_tokens}")
    print(f"Completion Tokens: {cb.completion_tokens}")
    print(f"Total Cost (USD): ${cb.total_cost}")

