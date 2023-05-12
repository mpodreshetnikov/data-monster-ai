from pydantic import Field

import re
from typing import Union

from langchain.base_language import BaseLanguageModel
from langchain.agents.agent import AgentOutputParser
from langchain.agents.mrkl.prompt import FORMAT_INSTRUCTIONS
from langchain.output_parsers.retry import RetryOutputParser
from langchain.prompts.base import StringPromptValue
from langchain.schema import AgentAction, AgentFinish, OutputParserException


FINAL_ANSWER_ACTIONS = [
    "answer:",
    "answer is:",
    "answer is ",
    ]


class CustomOutputParser(AgentOutputParser):
    is_debug: bool = Field(default=False)
    retrying_llm: BaseLanguageModel = Field(default=None)

    def get_format_instructions(self) -> str:
        return FORMAT_INSTRUCTIONS
    
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        format_instructions = self.get_format_instructions()
        inner_parser = __InnerCustomOutputParser__(is_debug=self.is_debug)

        if self.retrying_llm:
            retry_parser = RetryOutputParser.from_llm(
                llm=self.retrying_llm,
                parser=inner_parser)
            return retry_parser.parse_with_prompt(text, StringPromptValue(text=format_instructions))
        else:
            return inner_parser.parse(text)


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
            error_str = f"Could not parse LLM output: `{text}`"
            if self.is_debug:
                print(error_str)
            raise OutputParserException(error_str)
        action = match.group(1).strip()
        action_input = match.group(2)
        action_input = action_input.replace("```postgresql", "").replace("```sql", "").replace("```", "")
        return AgentAction(action, action_input.strip(" ").strip('"'), text)