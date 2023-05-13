from uuid import UUID
from pydantic import Field, PrivateAttr

import re
from typing import Any, Dict, List, Optional, Union

from langchain.base_language import BaseLanguageModel
from langchain.agents.agent import AgentOutputParser
from langchain.agents.mrkl.prompt import FORMAT_INSTRUCTIONS
from langchain.output_parsers.retry import RetryWithErrorOutputParser
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
    last_prompt_saver_callback_handler: LastPromptSaverCallbackHandler = Field()

    def get_format_instructions(self) -> str:
        return FORMAT_INSTRUCTIONS
    
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        inner_parser = __InnerCustomOutputParser__(is_debug=self.is_debug)
        if self.retrying_llm:
            retry_parser = RetryWithErrorOutputParser.from_llm(
                llm=self.retrying_llm,
                parser=inner_parser)
            prompt = self.last_prompt_saver_callback_handler._last_prompt
            return retry_parser.parse_with_prompt(text, StringPromptValue(text=prompt))
        else:
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
            if "Action: None" in text:
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