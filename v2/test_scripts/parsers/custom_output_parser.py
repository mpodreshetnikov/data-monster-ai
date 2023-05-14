from uuid import UUID
from langchain import LLMChain
from pydantic import Field

import re
from typing import Any, Dict, List, TypeVar, Union

from langchain.base_language import BaseLanguageModel
from langchain.agents.agent import AgentOutputParser
from langchain.agents.mrkl.prompt import FORMAT_INSTRUCTIONS
from langchain.output_parsers.retry import RetryWithErrorOutputParser
from langchain.prompts.base import StringPromptValue
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import (
    AgentAction,
    AgentFinish,
    OutputParserException,
    PromptValue,
)
from langchain.callbacks.manager import Callbacks

from prompts.agent_prompts import RETRY_WITH_ERROR_PROMPT


FINAL_ANSWER_ACTIONS = [
    "answer:",
    "answer is:",
    "answer is ",
    ]


class LastPromptSaverCallbackHandler(BaseCallbackHandler):
    _last_prompt: str = None
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> Any:
        prompt = prompts[0]
        self._last_prompt = prompt
        return prompt


class CustomAgentOutputParser(AgentOutputParser):
    is_debug: bool = Field(default=False)
    retrying_llm: BaseLanguageModel = Field(default=None)
    retrying_last_prompt_saver: LastPromptSaverCallbackHandler = Field()
    retrying_chain_callbacks: list[BaseCallbackHandler] = Field(default=[])

    def get_format_instructions(self) -> str:
        return FORMAT_INSTRUCTIONS
    
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        inner_parser = __InnerCustomAgentOutputParser__(is_debug=self.is_debug)
        if self.retrying_llm and self.retrying_last_prompt_saver:
            llm_chain = LLMChain(llm=self.retrying_llm, prompt=RETRY_WITH_ERROR_PROMPT)
            retry_parser = CustomRetryWithErrorOutputParser(parser=inner_parser, retry_chain=llm_chain, callbacks=self.retrying_chain_callbacks)
            prompt = self.retrying_last_prompt_saver._last_prompt
            if prompt:
                return retry_parser.parse_with_prompt(text, StringPromptValue(text=prompt))
        return inner_parser.parse(text)
        
    class Config:
        arbitrary_types_allowed = True


class __InnerCustomAgentOutputParser__(AgentOutputParser):
    is_debug = Field(default=False)

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        for final_answer_action in FINAL_ANSWER_ACTIONS:
            if final_answer_action in text.lower():
                return AgentFinish(
                    {"output": text.split(final_answer_action)[-1].strip()}, text
                )
        # \s matches against tab/newline/whitespace
        regex = (
            r"Action\s*\d*\s*:[\s]*(.*?)[\s]*Action\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)"
        )
        match = re.search(regex, text, re.DOTALL)
        if not match:
            if "Action: None" in text or "Action: N/A" in text:
                error_str = "Action was None, but you must specify an action from the list"
            else:
                error_str = "Action and Action Input were not provided"
            if self.is_debug:
                print(f"{error_str}:/n---/n{text}/n---/n")
            raise OutputParserException(error_str)
        action = match.group(1).strip()
        action_input = match.group(2)
        action_input = action_input.replace("```postgresql", "").replace("```sql", "").replace("```", "")
        return AgentAction(action, action_input.strip(" ").strip('"'), text)
    

T = TypeVar("T")
class CustomRetryWithErrorOutputParser(RetryWithErrorOutputParser[T]):
    """
    Wraps a parser and tries to fix parsing errors.
    Customed: passing inheritable callbacks to chain run.
    """
    callbacks: Callbacks
    
    def parse_with_prompt(self, completion: str, prompt_value: PromptValue) -> T:
        try:
            parsed_completion = self.parser.parse(completion)
        except OutputParserException as e:
            new_completion = self.retry_chain.run(
                prompt=prompt_value.to_string(),
                completion=completion,
                error=repr(e),
                callbacks=self.callbacks,
            )
            parsed_completion = self.parser.parse(new_completion)

        return parsed_completion
    
    class Config:
        arbitrary_types_allowed = True