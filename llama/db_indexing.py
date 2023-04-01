import configparser
import logging
import sys
from typing import Callable, Type, TypeVar
from sqlalchemy import create_engine
from llama_index import LLMPredictor, SQLDatabase, GPTSimpleVectorIndex
from llama_index.llm_predictor.chatgpt import ChatGPTLLMPredictor
from langchain.chat_models import ChatOpenAI
from llama_index.indices.base import BaseGPTIndex
from llama_index.indices.struct_store import SQLContextContainerBuilder
from llama_index.indices.query.query_runner import QueryRunner
from llama_index.indices.query.schema import QueryBundle, QueryConfig, QueryMode
from llama_index.indices.query.base import BaseGPTIndexQuery
import os

def create_query() -> BaseGPTIndexQuery:
    llm_predictor = __build_llm_predictor__()

    conn_str = __build_conn_string__('db', 'postgresql')
    sql_db = __build_sql_db__(conn_str)

    index = __with_cache__(
        GPTSimpleVectorIndex,
        lambda: __build_db_index__(GPTSimpleVectorIndex, sql_db, llm_predictor),
        llm_predictor,
        cache_name='query_index'
    )

    config = configparser.ConfigParser()
    config.read("settings.ini")
    tables_to_take: int = config.getint("db_schema", "TablesToTake")

    return __build_query_obj__(index, top_index_nodes_count=tables_to_take)


def get_most_similar_tables(query_obj: BaseGPTIndexQuery, question: str) -> list[str]:
    nodes = query_obj.get_nodes_and_similarities_for_response(QueryBundle(question))
    return list(map(lambda x: x[0].text, nodes))


def __build_llm_predictor__() -> LLMPredictor:
    config = configparser.ConfigParser()
    config.read("settings.ini")
    api_key: str = config["openai"]["ApiKey"]
    ChoicesOneRequest: int = int(config["openai"]["ChoicesOneRequest"])
    RequestTimeoutSeconds: int = int(config["openai"]["RequestTimeoutSeconds"])
    LimitRetries: int = int(config["openai"]["LimitRetries"])
    AiModel: str = config["openai"]["AiModel"]

    llm_predictor = ChatGPTLLMPredictor(ChatOpenAI(
        temperature=0.05,
        model_name=AiModel,
        openai_api_key=api_key,
        request_timeout=RequestTimeoutSeconds,
        max_retries=LimitRetries,
        n=ChoicesOneRequest,))
    
    return llm_predictor


def __build_db_index__(index_type: Type[BaseGPTIndex], sql_db: SQLDatabase, llm_predictor: LLMPredictor) -> BaseGPTIndex:
    context_builder = SQLContextContainerBuilder(sql_db)
    table_schema_index = context_builder.derive_index_from_context(
        index_type,
        llm_predictor=llm_predictor,
    )
    return table_schema_index


IndexType = TypeVar('IndexType', bound=BaseGPTIndex, covariant=True)
def __with_cache__(
        index_type: Type[IndexType],
        index_builder: Callable[[], IndexType],
        llm_predictor: LLMPredictor,
        cache_name: str) -> IndexType:
    dir = './indices/'
    index_path = os.path.join(dir, cache_name)
    if os.path.exists(index_path):
        index = index_type.load_from_disk(index_path, llm_predictor=llm_predictor)
    else:
        index = index_builder()
        os.makedirs(dir)
        index.save_to_disk(index_path)
    return index


def __build_query_obj__(index: BaseGPTIndex, top_index_nodes_count: int = 1) -> BaseGPTIndexQuery:
    query_config = QueryConfig(
        index_struct_type=index.index_struct.get_type(),
        query_mode=QueryMode(QueryMode.DEFAULT),
        query_kwargs={
            "similarity_top_k": top_index_nodes_count,
        },
    )
    query_runner = QueryRunner(
        index.llm_predictor,
        index.prompt_helper,
        index.embed_model,
        index.docstore,
        index.index_registry,
        query_configs=[query_config],
        query_transform=None,
        recursive=False,
        use_async=False,
    )
    query_obj = query_runner._get_query_obj(index.index_struct)
    return query_obj


def __build_conn_string__(config_db_name: str, db_type: str):
    config = configparser.ConfigParser()
    config.read("settings.ini")

    db_config_section = config[config_db_name]
    conn = {
        'host': db_config_section["Host"],
        'dbname': db_config_section["Database"],
        'user': db_config_section["User"],
        'password': db_config_section["Password"],
        'port': db_config_section["Port"],
    }

    return f"{db_type}://{conn['user']}:{conn['password']}@{conn['host']}:{conn['port']}/{conn['dbname']}"


def __build_sql_db__(conn_string: str) -> SQLDatabase:
    engine = create_engine(conn_string)
    sql_database = SQLDatabase(engine)
    return sql_database