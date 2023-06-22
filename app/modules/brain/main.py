from enum import Enum
import logging
from dataclasses import dataclass
from typing import Any
import asyncio

from langchain import LLMChain, SQLDatabase
from langchain.base_language import BaseLanguageModel
from langchain.embeddings.base import Embeddings
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.schema import OutputParserException, AgentAction, AgentFinish
from langchain.chains.base import Chain
from langchain.chains import SimpleSequentialChain
from langchain.callbacks.base import BaseCallbackManager
from langchain.callbacks.manager import Callbacks
from langchain.agents.agent import AgentExecutor
from langchain.agents.agent_toolkits.sql.prompt import SQL_SUFFIX
from langchain.agents.mrkl.base import ZeroShotAgent
from langchain.agents.mrkl.prompt import FORMAT_INSTRUCTIONS
from langchain.callbacks import get_openai_callback
from openai import InvalidRequestError

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from modules.brain.llm.tools.db_data_interaction.toolkit import DbDataInteractionToolkit
from modules.brain.llm.prompts.sql_agent_prompts import (
    SQL_PREFIX,
    get_formatted_hints,
    get_sql_suffix_with_hints,
)
from modules.brain.llm.prompts.translator_prompts import TRANSLATOR_PROMPT
from modules.brain.llm.prompts.chart_prompts import (
    GET_CHART_PARAMS_PROMPT,
    ChartParams,
    build_data_example_for_prompt,
)
from modules.brain.llm.prompts.clarifying_question_prompts import (
    CLARIFYING_QUESTION_PROMPT,
    ClarifyingQuestionParams,
)
from modules.brain.llm.monitoring.callback import LogLLMRayCallbackHandler
from modules.brain.llm.parsers.custom_output_parser import CustomAgentOutputParser
from modules.brain.llm.parsers.custom_output_parser import LastPromptSaverCallbackHandler
from modules.common.errors import (
    add_info_to_exception, AgentLimitExceededAnswerException, SQLTimeoutAnswerException, 
    CreatedNotWorkingSQLAnswerException, NoDataReturnedFromDBAnswerException, LLMContextExceededAnswerException)
from modules.common.sql_helpers import update_limit

from modules.data_access.main import InternalDB
from modules.data_access.models.brain_response_data import BrainResponseType


logger = logging.getLogger(__name__)


@dataclass
class Answer:
    question: str
    ray_id: str
    answer_text: str | None = None
    sql_script: str | None = None
    chart_params: ChartParams | None = None
    chart_data: list[dict] | None = None


class BrainMode(Enum):
    SHORT = 1
    """Minimum agent iterations"""
    DEFAULT = 2
    """Default agent iterations"""


class Constants:
    MIN_SQL_AGENT_ITERATIONS = 2
    """By the statistics, bot answers correctly instantly in 85% cases (for good questions)"""
    DEFAULT_SQL_AGENT_ITERATIONS = 4
    """By the statistics, bot answers correctly in 3-4 iterations in 100% cases (for good questions)"""


class Brain:
    db: SQLDatabase
    default_llm: BaseLanguageModel
    default_embeddings: Embeddings

    _prompt_log_path: str | None = None
    _inheritable_llm_callbacks: Callbacks = []
    _verbose: bool = False
    _default_sql_llm_toolkit: DbDataInteractionToolkit
    _sql_query_hints_limit: int = 0

    def __init__(
        self,
        db: SQLDatabase,
        llm: BaseLanguageModel | None = None,
        embeddings: Embeddings | None = None,
        db_hints_doc_path: str | None = None,
        db_comments_override_path: str | None = None,
        sql_query_examples_path: str | None = None,
        sql_query_hints_limit: int = 0,
        verbose: bool = False,
        prompt_log_path: str | None = None,
        internal_db: InternalDB | None = None,
        clarifying_question_llm:  BaseLanguageModel | None = None,
    ) -> None:
        self.db = db
        self._verbose = verbose
        self._sql_query_hints_limit = sql_query_hints_limit
        self._prompt_log_path = prompt_log_path
        self.internal_db = internal_db
        if not embeddings:
            logger.warning("No embeddings provided, using default OpenAIEmbeddings")
        self.default_embeddings = embeddings or OpenAIEmbeddings()
        if not llm:
            logger.warning("No llm provided, using default ChatOpenAI")
        self.default_llm = llm or ChatOpenAI(verbose=self._verbose)
        self.clarifying_question_llm = clarifying_question_llm
        self._default_sql_llm_toolkit = self.__build_sql_llm_toolkit(
            db_hints_doc_path, db_comments_override_path, sql_query_examples_path
        )

    async def answer(self, question: str, ray_id: str, mode: BrainMode = BrainMode.DEFAULT) -> Answer:
        ray_logger = LogLLMRayCallbackHandler(self._prompt_log_path, ray_id=ray_id)
        answer = Answer(question, ray_id)

        sql_agent_iter_limit = (
            Constants.MIN_SQL_AGENT_ITERATIONS
            if mode == BrainMode.SHORT
            else Constants.DEFAULT_SQL_AGENT_ITERATIONS
        )
        answer.answer_text = await self.__provide_text_answer(question, ray_logger, ray_id, sql_agent_iter_limit)

        answer.sql_script = ray_logger.get_sql_script()

        try:
            answer.chart_params = await self.__provide_chart_params(
                answer, ray_logger=ray_logger
            )
            if answer.chart_params:
                answer.chart_data = await self.__get_chart_data(answer)
        except Exception:
            answer.chart_params = None

        await self.__save_brain_response(answer)
        return answer

    async def make_clarifying_question(self, context: str, ray_id: str) -> ClarifyingQuestionParams | None:
        ray_logger = LogLLMRayCallbackHandler(self._prompt_log_path, ray_id=ray_id)

        chain = LLMChain(
            llm=self.clarifying_question_llm or self.default_llm,
            prompt=CLARIFYING_QUESTION_PROMPT,
            verbose=self._verbose,
        )
        with get_openai_callback() as openai_cb:
            try:
                result: ClarifyingQuestionParams | None = await chain.apredict_and_parse(
                    callbacks=[ray_logger] if ray_logger else [],
                    context=context,
                ) # type: ignore
            finally:
                logger.info(openai_cb)

        if not result:
            return None

        answer = Answer(context, ray_id, result.clarifying_question)
        await self.__save_brain_response(answer, BrainResponseType.CLARIFYING_QUESTION)

        return result

    async def __save_brain_response(self, answer: Answer, type: BrainResponseType = BrainResponseType.SQL) -> None:
        try:
            await self.internal_db.brain_response_repository.add(
                answer.ray_id, answer.question, answer.answer_text or "", answer.sql_script, type
            )
        except Exception as e:
            logger.error(e, exc_info=True)
            
    async def __provide_text_answer(
        self, question: str, ray_logger: LogLLMRayCallbackHandler, ray_id: str, sql_agent_iter_limit: int = 5
    ) -> str:
        last_prompt_saver = LastPromptSaverCallbackHandler()
        sql_agent_chain =  await self.__build_sql_agent_chain(
            question, last_prompt_saver, agent_iter_limit=sql_agent_iter_limit)
        lang_translator_chain = self.__build_lang_translator_chain()

        overall_chain = SimpleSequentialChain(
            chains=[sql_agent_chain, lang_translator_chain],
            verbose=self._verbose,
        )

        with get_openai_callback() as openai_cb:
            try:
                response = await overall_chain.arun(
                    question,
                    callbacks=[last_prompt_saver, ray_logger, *self._inheritable_llm_callbacks],)
            except OutputParserException as e:
                logger.error("Parser cannot parse AI answer", exc_info=True)
                e = add_info_to_exception(e, "ray_id", ray_id)
                raise e
            except InvalidRequestError as e:
                logger.error("Error while asking OpenAI", exc_info=True)
                e = add_info_to_exception(e, "ray_id", ray_id)
                raise e
            except Exception as e:
                e = add_info_to_exception(e, "ray_id", ray_id)
                raise e
            finally:
                logger.info(openai_cb)
        
        # do checks even the answer is got
        sql = ray_logger.get_sql_script()
        if sql:
            data = None
            try:
                async with self.db._async_engine.begin() as connection:
                    result = await connection.execute(text(sql))
                    rows = result.fetchall()
                    columns = result.keys()
                    data: list[dict] = [dict(zip(columns, row)) for row in rows]
            except (OperationalError, asyncio.TimeoutError):
                if ray_logger.was_sql_timeout_error:
                    e = SQLTimeoutAnswerException()
                    e = add_info_to_exception(
                        e, "ray_id", ray_id)
                    raise e
            except Exception as e:
                logger.error(f"Error while executing SQL, ray_id: {ray_id}", exc_info=True)
                e = CreatedNotWorkingSQLAnswerException()
                e = add_info_to_exception(
                    e, "ray_id", ray_id)
                raise e
            if not data or (
                # test if data contains only one row with one value and it is False (0, no data, empty string)
                len(data) == 1 and len(data[0]) == 1 and not bool(list(data[0].values())[0])
            ):
                e = NoDataReturnedFromDBAnswerException()
                e = add_info_to_exception(
                    e, "ray_id", ray_id)
                raise e
            return response
        e = CreatedNotWorkingSQLAnswerException()
        e = add_info_to_exception(
                    e, "ray_id", ray_id)
        raise e

    def __build_sql_llm_toolkit(
        self,
        db_hints_doc_path: str = None,
        db_comments_override_path: str = None,
        sql_query_examples_path: str = None,
        llm: BaseLanguageModel = None,
    ) -> DbDataInteractionToolkit:
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

    async def __build_sql_agent_chain(
        self,
        question: str,
        last_prompt_saver: LastPromptSaverCallbackHandler,
        llm: BaseLanguageModel | None = None,
        agent_iter_limit: int = 5,
    ) -> Chain:
        hints_str = await get_formatted_hints(
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

        agent_executor = self.__build_sql_agent_executor(
            llm=llm or self.default_llm,
            suffix=agent_suffix,
            output_parser=output_parser,
            agent_iter_limit=agent_iter_limit,
        )

        return agent_executor


    def __build_sql_agent_executor(
        self,
        llm: BaseLanguageModel,
        callback_manager: BaseCallbackManager | None = None,
        prefix: str = SQL_PREFIX,
        suffix: str = SQL_SUFFIX,
        format_instructions: str = FORMAT_INSTRUCTIONS,
        input_variables: list[str] | None = None,
        top_k: int = 10,
        max_execution_time: float | None = None,
        early_stopping_method: str = "force",
        agent_executor_kwargs: dict[str, Any] | None = None,
        agent_iter_limit: int = 5,
        **kwargs,
    ):
        """
        Build SQL agent executor.
        Rewrite original building method to raise exception when exec limit is exceeded.
        """
        tools = self._default_sql_llm_toolkit.get_tools()
        prefix = prefix.format(dialect=self._default_sql_llm_toolkit.dialect, top_k=top_k)
        prompt = ZeroShotAgent.create_prompt(
            tools,
            prefix=prefix,
            suffix=suffix,
            format_instructions=format_instructions,
            input_variables=input_variables,
        )
        llm_chain = LLMChain(
            llm=llm,
            prompt=prompt,
            callback_manager=callback_manager,
        )
        tool_names = [tool.name for tool in tools]

        class ZeroShotAgentRaising(ZeroShotAgent):
            def return_stopped_response(
                self,
                early_stopping_method: str,
                intermediate_steps: list[tuple[AgentAction, str]],
                **kwargs: Any
            ) -> AgentFinish:
                inputs = self.get_full_inputs(intermediate_steps, **kwargs)
                question = inputs.get("input", "")
                agent_work = inputs.get("agent_scratchpad", "")
                agent_work_text = f"Question:{question}\n{agent_work}"
                raise AgentLimitExceededAnswerException(agent_work_text=agent_work_text)
        agent = ZeroShotAgentRaising(llm_chain=llm_chain, allowed_tools=tool_names, **kwargs)
        return AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=tools,
            callback_manager=callback_manager,
            verbose=self._verbose,
            max_iterations=agent_iter_limit,
            max_execution_time=max_execution_time,
            early_stopping_method=early_stopping_method,
            **(agent_executor_kwargs or {}),
        )

    def __build_lang_translator_chain(self, llm: BaseLanguageModel | None = None) -> Chain:
        translator_chain = LLMChain(
            llm=llm or self.default_llm, prompt=TRANSLATOR_PROMPT
        )
        return translator_chain

    async def __provide_chart_params(
        self,
        answer: Answer,
        llm: BaseLanguageModel = None,
        ray_logger: LogLLMRayCallbackHandler = None,
    ) -> ChartParams | None:
        _EXAMPLES_LIMIT = 3
        _DEFAULT = None

        if not answer or not answer.sql_script:
            return _DEFAULT

        sql = update_limit(answer.sql_script, _EXAMPLES_LIMIT)

        try:
            async with self.db._async_engine.begin() as connection:
                result = await connection.execute(text(sql))
                rows = result.fetchall()
                columns = result.keys()
                data: list[dict] = [dict(zip(columns, row)) for row in rows]
        except Exception:
            logger.warning(
                "Failed to execute sql for chart example data", exc_info=True
            )
            return _DEFAULT
        if not data:
            return _DEFAULT

        data_example = build_data_example_for_prompt(data, _EXAMPLES_LIMIT)

        chain = LLMChain(
            llm=llm or self.default_llm,
            prompt=GET_CHART_PARAMS_PROMPT,
            verbose=self._verbose,
        )
        try:
            result = await chain.apredict_and_parse(
                callbacks=[ray_logger] if ray_logger else [],
                question=answer.question,
                data_example=data_example,
            )
        except Exception:
            logger.warning("Failed to get chart params", exc_info=True)
            return _DEFAULT

        return result

    async def __get_chart_data(self, answer: Answer) -> list[dict] | None:
        _DEFAULT: list[dict] | None = None

        if not answer.chart_params:
            return _DEFAULT
        sql = update_limit(answer.sql_script, answer.chart_params.limit)
        if not sql:
            logger.warning("Failed to update sql with limit")
            return _DEFAULT
        try:
            async with self.db._async_engine.begin() as connection:
                result = await connection.execute(text(sql))
                rows = result.fetchall()
                columns = result.keys()
                data: list[dict] = [dict(zip(columns, row)) for row in rows]
        except Exception:
            logger.warning("Failed to execute sql for chart data", exc_info=True)
            return _DEFAULT

        if not data:
            return _DEFAULT

        if (
            not answer.chart_params.label_column
            or answer.chart_params.label_column not in data[0].keys()
        ):
            logger.warning("Failed to find label column in data")
            return _DEFAULT

        if not answer.chart_params.value_columns:
            logger.warning("Failed to find value columns")
            return _DEFAULT

        supported_value_columns = list(
            filter(
                lambda column: column in data[0].keys(),
                answer.chart_params.value_columns,
            )
        )
        if not supported_value_columns:
            logger.warning("Failed to find any of value columns in data")
            return _DEFAULT

        keys_to_retrieve = [answer.chart_params.label_column, *supported_value_columns]
        data = [
            {key: row[key] for key in keys_to_retrieve if key in row.keys()}
            for row in data
        ]
        return data
