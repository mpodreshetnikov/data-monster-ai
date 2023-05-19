import logging
from dataclasses import dataclass

from langchain import LLMChain, SQLDatabase
from langchain.base_language import BaseLanguageModel
from langchain.embeddings.base import Embeddings
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.agents.agent_toolkits.base import BaseToolkit
from langchain.agents.mrkl.output_parser import OutputParserException
from langchain.chains.base import Chain
from langchain.chains import SimpleSequentialChain
from langchain.callbacks.manager import Callbacks
from langchain.agents import create_sql_agent
from langchain.callbacks import get_openai_callback
from openai import InvalidRequestError

from modules.brain.llm.tools.db_data_interaction.toolkit import DbDataInteractionToolkit
from modules.brain.llm.prompts.sql_agent_prompts import SQL_PREFIX, get_formatted_hints, get_sql_suffix_with_hints
from modules.brain.llm.prompts.translator_prompts import TRANSLATOR_PROMPT
from modules.brain.llm.monitoring.callback import LogLLMRayCallbackHandler
from modules.brain.llm.parsers.custom_output_parser import CustomAgentOutputParser
from modules.brain.llm.parsers.custom_output_parser import LastPromptSaverCallbackHandler
from modules.common.errors import add_info_to_exception
from modules.localdb.service_sql import SQLService

logger = logging.getLogger(__name__)


class Brain:
    @dataclass
    class Answer:
        ray_id: str
        text: str
        
    db: SQLDatabase
    default_llm: BaseLanguageModel
    default_embeddings: Embeddings
    
    _prompt_log_path: str = None
    _inheritable_llm_callbacks: Callbacks = []
    _verbose: bool = False
    _default_sql_llm_toolkit: DbDataInteractionToolkit = None
    _sql_query_hints_limit: int = 0
    _sql_agent_max_iterations: int = 5
    
    
    def __init__(
            self,
            db: SQLDatabase,
            llm: BaseLanguageModel = None,
            embeddings: Embeddings = None,
            db_hints_doc_path: str = None,
            sql_query_examples_path: str = None,
            sql_query_hints_limit: int = 0,
            sql_agent_max_iterations: int = 5,
            verbose: bool = False,
            prompt_log_path: str = None,
        ) -> None:
        self.db = db
        self._verbose = verbose
        self._sql_query_hints_limit = sql_query_hints_limit
        self._sql_agent_max_iterations = sql_agent_max_iterations
        self._prompt_log_path = prompt_log_path
        if not embeddings:
            logger.warning("No embeddings provided, using default OpenAIEmbeddings")
        self.default_embeddings = embeddings or OpenAIEmbeddings()
        if not llm:
            logger.warning("No llm provided, using default ChatOpenAI")
        self.default_llm = llm or ChatOpenAI(verbose=self._verbose)
        self._default_sql_llm_toolkit = self.__build_sql_llm_toolkit(db_hints_doc_path, sql_query_examples_path)
        self.sql_service = SQLService()

    def answer(self, question: str) -> Answer:
        last_prompt_saver = LastPromptSaverCallbackHandler()
        sql_agent_chain = self.__build_sql_agent_chain__(question, last_prompt_saver)
        lang_translator_chain = self.__build_lang_translator_chain__()
        
        overall_chain = SimpleSequentialChain(
            chains=[sql_agent_chain, lang_translator_chain],
            verbose=self._verbose,)
        
        ray_logger = LogLLMRayCallbackHandler(self._prompt_log_path)
        with get_openai_callback() as openai_cb:
            try:
                response = overall_chain.run(
                    question,
                    callbacks=[last_prompt_saver, ray_logger, *self._inheritable_llm_callbacks],)
            except OutputParserException as e:
                logger.error("Parser cannot parse AI answer", exc_info=True)
                e = add_info_to_exception(e, "ray_id", ray_logger.get_ray_str())
                raise e
            except InvalidRequestError as e:
                logger.error("Error while asking OpenAI", exc_info=True)
                e = add_info_to_exception(e, "ray_id", ray_logger.get_ray_str())
                raise e
            except Exception as e:
                e = add_info_to_exception(e, "ray_id", ray_logger.get_ray_str())
                raise e
            logger.info(openai_cb)
        
        self.sql_service.save_sql_str(ray_logger.sql)
        return self.Answer(ray_logger.get_ray_str(), response)
        
    
    def __build_sql_llm_toolkit(
            self,
            db_hints_doc_path: str = None,
            sql_query_examples_path: str = None,
            llm: BaseLanguageModel = None,
        ) -> BaseToolkit:
        toolkit = DbDataInteractionToolkit(
            db=self.db,
            llm=llm or self.default_llm,
            embeddings=self.default_embeddings,
            db_hints_doc_path=db_hints_doc_path,
            sql_query_examples_path=sql_query_examples_path,
            )
        with get_openai_callback() as openai_cb:
            toolkit.build()
            if self._verbose:
                logger.info(f"Toolkit builded successfully\n{openai_cb}")
        return toolkit
    
    def __build_sql_agent_chain__(
            self,
            question: str,
            last_prompt_saver: LastPromptSaverCallbackHandler,
            llm: BaseLanguageModel = None
        ) -> Chain:
        hints_str = get_formatted_hints(
                self._default_sql_llm_toolkit,
                question,
                self._sql_query_hints_limit,
            )
        agent_suffix = get_sql_suffix_with_hints(hints_str)
        
        output_parser = CustomAgentOutputParser(
                retrying_llm=llm or self.default_llm,
                verbose=self._verbose,
                retrying_last_prompt_saver=last_prompt_saver,
                retrying_chain_callbacks=self._inheritable_llm_callbacks,
            )
        
        agent_executor = create_sql_agent(
                llm=llm or self.default_llm,
                toolkit=self._default_sql_llm_toolkit,
                verbose=self._verbose,
                prefix=SQL_PREFIX,
                suffix=agent_suffix,
                output_parser=output_parser,
                max_iterations=self._sql_agent_max_iterations,
            )
        
        return agent_executor
    
    def __build_lang_translator_chain__(self, llm: BaseLanguageModel = None) -> Chain:
        translator_chain = LLMChain(
                llm=llm or self.default_llm, 
                prompt=TRANSLATOR_PROMPT)
        return translator_chain