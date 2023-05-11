import re
from typing import Union

from langchain.agents.agent import AgentOutputParser
from langchain.agents.mrkl.prompt import FORMAT_INSTRUCTIONS
from langchain.schema import AgentAction, AgentFinish, OutputParserException

FINAL_ANSWER_ACTIONS = [
    "final answer:",
    "answer is:",]

class CustomOutputParser(AgentOutputParser):
    def get_format_instructions(self) -> str:
        return FORMAT_INSTRUCTIONS

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
            raise OutputParserException(f"Could not parse LLM output: `{text}`")
        action = match.group(1).strip()
        action_input = match.group(2)
        action_input = action_input.replace("```postgresql", "").replace("```sql", "").replace("```", "")
        return AgentAction(action, action_input.strip(" ").strip('"'), text)