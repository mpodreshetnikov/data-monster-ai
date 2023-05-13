from uuid import UUID
from langchain import LLMChain
from pydantic import Field, PrivateAttr

import re
from typing import Any, Dict, List, Optional, Union

from langchain.base_language import BaseLanguageModel
from langchain.agents.agent import AgentOutputParser
from langchain.agents.mrkl.prompt import FORMAT_INSTRUCTIONS
from langchain.output_parsers.retry import RetryWithErrorOutputParser, NAIVE_RETRY_WITH_ERROR_PROMPT
from langchain.prompts.base import StringPromptValue
from langchain.schema import AgentAction, AgentFinish, OutputParserException
from langchain.callbacks.base import BaseCallbackHandler


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


class CustomOutputParserWithCallbackHandling(AgentOutputParser, BaseCallbackHandler):
    is_debug: bool = Field(default=False)
    retrying_llm: BaseLanguageModel = Field(default=None)
    retrying_last_prompt_saver: LastPromptSaverCallbackHandler = Field()
    retrying_chain_callbacks: list[BaseCallbackHandler] = Field(default=[])

    def get_format_instructions(self) -> str:
        return FORMAT_INSTRUCTIONS
    
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        inner_parser = __InnerCustomOutputParser__(is_debug=self.is_debug)
        if self.retrying_llm and self.retrying_last_prompt_saver:
            llm_chain = LLMChain(llm=self.retrying_llm, prompt=NAIVE_RETRY_WITH_ERROR_PROMPT, callbacks=self.retrying_chain_callbacks)
            retry_parser = RetryWithErrorOutputParser(parser=inner_parser, retry_chain=llm_chain)
            prompt = self.retrying_last_prompt_saver._last_prompt
            if prompt:
                return retry_parser.parse_with_prompt(text, StringPromptValue(text=prompt))
        return inner_parser.parse(text)
        
    class Config:
        arbitrary_types_allowed = True


class __InnerCustomOutputParser__(AgentOutputParser):
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
                error_str = "Action was None, but you must specify an action from the list."
            else:
                error_str = "Action and Action Input were not provided."
            if self.is_debug:
                print(error_str)
            raise OutputParserException(error_str)
        action = match.group(1).strip()
        action_input = match.group(2)
        action_input = action_input.replace("```postgresql", "").replace("```sql", "").replace("```", "")
        return AgentAction(action, action_input.strip(" ").strip('"'), text)