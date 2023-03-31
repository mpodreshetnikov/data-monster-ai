import configparser
import logging
import sys
from sqlalchemy import create_engine
from llama_index import SQLDatabase, GPTSQLStructStoreIndex, GPTSimpleVectorIndex
from llama_index.llm_predictor.chatgpt import ChatGPTLLMPredictor
from langchain.chat_models import ChatOpenAI
from llama_index.indices.struct_store import SQLContextContainerBuilder
from llama_index.indices.query.query_runner import QueryRunner
from llama_index.indices.query.schema import QueryBundle, QueryConfig, QueryMode
import os

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, force=True)

config = configparser.ConfigParser()
config.read("settings.ini")

db_config_section = config['db']
conn = {
    'host': db_config_section["Host"],
    'dbname': db_config_section["Database"],
    'user': db_config_section["User"],
    'password': db_config_section["Password"],
    'port': db_config_section["Port"],
}

engine = create_engine(f"postgresql://{conn['user']}:{conn['password']}@{conn['host']}:{conn['port']}/{conn['dbname']}")
sql_database = SQLDatabase(engine)


api_key: str = config["openai"]["ApiKey"]
MaxAnswerTokens: int = int(config["openai"]["MaxAnswerTokens"])
ChoicesOneRequest: int = int(config["openai"]["ChoicesOneRequest"])
TestMode: bool = config.getboolean("openai", "TestMode")
RequestTimeoutSeconds: int = int(config["openai"]["RequestTimeoutSeconds"])
LimitRetries: int = int(config["openai"]["LimitRetries"])
RetriesTimeoutSeconds: int = int(config["openai"]["RetriesTimeoutSeconds"])
AiModel: str = config["openai"]["AiModel"]
AiModelType: str = config["openai"]["AiModelType"]

llm_predictor = ChatGPTLLMPredictor(ChatOpenAI(
    temperature=0.05,
    model_name=AiModel,
    openai_api_key=api_key,
    request_timeout=RequestTimeoutSeconds,
    max_retries=LimitRetries,
    n=ChoicesOneRequest,))


# BUILD DB INDEX
table_schema_index_path = "table_schema_index"
if os.path.exists(table_schema_index_path):
    table_schema_index = GPTSimpleVectorIndex.load_from_disk(table_schema_index_path, llm_predictor=llm_predictor)
else:
    context_builder = SQLContextContainerBuilder(sql_database)
    table_schema_index = context_builder.derive_index_from_context(
        GPTSimpleVectorIndex,
        llm_predictor=llm_predictor,
    )
    table_schema_index.save_to_disk(table_schema_index_path)


# BUILD QUERY RUNNER FOR DB INDEX
top_index_nodes_count = 3
query_config = QueryConfig(
    index_struct_type=table_schema_index.index_struct.get_type(),
    query_mode=QueryMode(QueryMode.DEFAULT),
    query_kwargs={
        "similarity_top_k": top_index_nodes_count,
    },
)
query_runner = QueryRunner(
    table_schema_index.llm_predictor,
    table_schema_index.prompt_helper,
    table_schema_index.embed_model,
    table_schema_index.docstore,
    table_schema_index.index_registry,
    query_configs=[query_config],
    query_transform=None,
    recursive=False,
    use_async=False,
)
query_obj = query_runner._get_query_obj(table_schema_index.index_struct)




question = "first names of 100 pupil users"
top_index_nodes = query_obj.get_nodes_and_similarities_for_response(QueryBundle(question))





DEFAULT_CONTEXT_QUERY_TMPL = (
    "Please return the relevant tables (including the full schema) "
    "for the following query: {orig_query_str}"
)
test = table_schema_index.index_registry
response = table_schema_index.query(question)
context_str = str(response.response)

context_container = context_builder.build_context_container()


sql_index = GPTSQLStructStoreIndex(
    llm_predictor=llm_predictor,
    sql_database=sql_database,
)
response = sql_index.query(question, sql_context_container=context_container)
print(response)