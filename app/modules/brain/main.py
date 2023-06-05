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
from sqlalchemy import text

from modules.brain.llm.tools.db_data_interaction.toolkit import DbDataInteractionToolkit
from modules.brain.llm.prompts.sql_agent_prompts import SQL_PREFIX, get_formatted_hints, get_sql_suffix_with_hints
from modules.brain.llm.prompts.translator_prompts import TRANSLATOR_PROMPT
from modules.brain.llm.prompts.chart_prompts import GET_CHART_PARAMS_PROMPT, ChartParams, build_data_example_for_prompt
from modules.brain.llm.monitoring.callback import LogLLMRayCallbackHandler
from modules.brain.llm.parsers.custom_output_parser import CustomAgentOutputParser
from modules.brain.llm.parsers.custom_output_parser import LastPromptSaverCallbackHandler
from modules.common.errors import add_info_to_exception
from modules.common.sql_helpers import update_limit

from modules.data_access.main import InternalDB

from modules.data_access.models.brain_response_data import BrainResponseData


logger = logging.getLogger(__name__)


@dataclass
class Answer:
    question: str
    ray_id: str
    answer_text: str | None = None
    sql_script: str | None = None
    chart_params: ChartParams | None = None
    chart_data: list[dict] | None = None

class Brain:
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
        llm: BaseLanguageModel | None = None,
        embeddings: Embeddings | None = None,
        db_hints_doc_path: str | None = None,
        db_comments_override_path: str | None = None,
        sql_query_examples_path: str | None = None,
        sql_query_hints_limit: int = 0,
        sql_agent_max_iterations: int = 5,
        verbose: bool = False,
        prompt_log_path: str | None = None,
        internal_db: InternalDB | None = None
    ) -> None:
        self.db = db
        self._verbose = verbose
        self._sql_query_hints_limit = sql_query_hints_limit
        self._sql_agent_max_iterations = sql_agent_max_iterations
        self._prompt_log_path = prompt_log_path
        self.internal_db = internal_db
        if not embeddings:
            logger.warning(
                "No embeddings provided, using default OpenAIEmbeddings")
        self.default_embeddings = embeddings or OpenAIEmbeddings()
        if not llm:
            logger.warning("No llm provided, using default ChatOpenAI")
        self.default_llm = llm or ChatOpenAI(verbose=self._verbose)
        self._default_sql_llm_toolkit = self.__build_sql_llm_toolkit(
            db_hints_doc_path, db_comments_override_path, sql_query_examples_path)

    def answer(self, question: str) -> Answer:
        ray_logger = LogLLMRayCallbackHandler(self._prompt_log_path)
        answer = Answer(question, ray_logger.get_ray_str())
        answer.answer_text = self.__provide_text_answer(question, ray_logger)
        answer.sql_script = ray_logger.get_sql_script()

        try:
            answer.chart_params = await self.__provide_chart_params(answer, ray_logger=ray_logger)
            if answer.chart_params:
                answer.chart_data = self.__get_chart_data(answer)
        except Exception:
            answer.chart_params = None

        self.__save_brain_response(answer)
        return answer

    def __save_brain_response(self, answer: Answer) -> None:
        try:
            with self.internal_db.Session() as session:
                brain_response_data = BrainResponseData(
                    ray_id=answer.ray_id, sql_script=answer.sql_script)
                session.add(brain_response_data)
                session.commit()
        except Exception:
            logger.error("failed to write to database", exc_info=True)

    def __provide_text_answer(self, question: str, ray_logger: LogLLMRayCallbackHandler) -> str:
        last_prompt_saver = LastPromptSaverCallbackHandler()
        sql_agent_chain = self.__build_sql_agent_chain(
            question, last_prompt_saver)
        lang_translator_chain = self.__build_lang_translator_chain()

        overall_chain = SimpleSequentialChain(
            chains=[sql_agent_chain, lang_translator_chain],
            verbose=self._verbose,)

        with get_openai_callback() as openai_cb:
            try:
                response = overall_chain.run(
                    question,
                    callbacks=[last_prompt_saver, ray_logger, *self._inheritable_llm_callbacks],)
            except OutputParserException as e:
                logger.error("Parser cannot parse AI answer", exc_info=True)
                e = add_info_to_exception(
                    e, "ray_id", ray_logger.get_ray_str())
                raise e
            except InvalidRequestError as e:
                logger.error("Error while asking OpenAI", exc_info=True)
                e = add_info_to_exception(
                    e, "ray_id", ray_logger.get_ray_str())
                raise e
            except Exception as e:
                e = add_info_to_exception(
                    e, "ray_id", ray_logger.get_ray_str())
                raise e
            logger.info(openai_cb)

        return response

    def __build_sql_llm_toolkit(
        self,
        db_hints_doc_path: str = None,
        db_comments_override_path: str = None,
        sql_query_examples_path: str = None,
        llm: BaseLanguageModel = None,
    ) -> BaseToolkit:
        toolkit = DbDataInteractionToolkit(
            db=self.db,
            llm=llm or self.default_llm,
            embeddings=self.default_embeddings,
            db_hints_doc_path=db_hints_doc_path,
            db_comments_override_path=db_comments_override_path,
            sql_query_examples_path=sql_query_examples_path,
        )
        with get_openai_callback() as openai_cb:
            toolkit.build()
            if self._verbose:
                logger.info(f"Toolkit builded successfully\n{openai_cb}")
        return toolkit

    def __build_sql_agent_chain(
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

    def __build_lang_translator_chain(self, llm: BaseLanguageModel = None) -> Chain:
        translator_chain = LLMChain(
            llm=llm or self.default_llm,
            prompt=TRANSLATOR_PROMPT)
        return translator_chain
    
    async def __provide_chart_params(self, answer: Answer, llm: BaseLanguageModel = None, ray_logger: LogLLMRayCallbackHandler = None) -> ChartParams | None:
        _EXAMPLES_LIMIT = 3
        _DEFAULT = None

        if not answer or not answer.sql_script:
            return _DEFAULT
        
        sql = update_limit(answer.sql_script, _EXAMPLES_LIMIT)
        try:
            with self.db._engine.connect() as connection:
                data: list[dict] = connection.execute(text(sql)).mappings().all()
        except Exception:
            logger.warning("Failed to execute sql for chart example data", exc_info=True)
            return _DEFAULT
        if not data or len(data) == 0:
            return _DEFAULT
        
        data_example = build_data_example_for_prompt(data, _EXAMPLES_LIMIT)

        chain = LLMChain(llm=llm or self.default_llm, prompt=GET_CHART_PARAMS_PROMPT, verbose=self._verbose)
        try:
            result = await chain.apredict_and_parse(
                callbacks=[ray_logger] if ray_logger else [],
                question=answer.question,
                data_example=data_example)
        except Exception:
            logger.warning("Failed to get chart params", exc_info=True)
            return _DEFAULT

        return result
    
    def __get_chart_data(self, answer: Answer) -> list[dict] | None:
        _DEFAULT: list[dict] | None = None

        if not answer.chart_params:
            return _DEFAULT
        sql = update_limit(answer.sql_script, answer.chart_params.limit)
        if not sql:
            logger.warning("Failed to update sql with limit")
            return _DEFAULT
        try:
            with self.db._engine.connect() as connection:
                data: list[dict] = connection.execute(text(sql)).mappings().all()
        except Exception:
            logger.warning("Failed to execute sql for chart data", exc_info=True)
            return _DEFAULT
        
        if not data:
            return _DEFAULT
        
        if not answer.chart_params.label_column or answer.chart_params.label_column not in data[0].keys():
            logger.warning("Failed to find label column in data")
            return _DEFAULT

        if not answer.chart_params.value_columns:
            logger.warning("Failed to find value columns")
            return _DEFAULT
        
        supported_value_columns = list(filter(lambda column: column in data[0].keys(), answer.chart_params.value_columns))
        if len(supported_value_columns) == 0:
            logger.warning("Failed to find any of value columns in data")
            return _DEFAULT

        keys_to_retrieve = [answer.chart_params.label_column, *supported_value_columns]
        data = [{key: row[key] for key in keys_to_retrieve if key in row.keys()} for row in data]
        return data

