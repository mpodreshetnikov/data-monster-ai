from dataclasses import dataclass
from enum import Enum
from langchain import PromptTemplate
from langchain.schema import BaseOutputParser


CLARIFYING_QUESTION = """Write any clarifying questions for text: {context}"""


@dataclass
class ClarifyingQuestionParams:
    class Action(Enum):
        Restart = "restart"
        Clarify = "clarify"
    action: Action = Action.Restart
    clarifying_question: str | None = None


class ClarifyingQuestionOutputParser(BaseOutputParser):
    def parse(self, text: str) -> ClarifyingQuestionParams | None:
        return ClarifyingQuestionParams()


CLARIFYING_QUESTION_PROMPT = PromptTemplate.from_template(
    CLARIFYING_QUESTION, output_parser=ClarifyingQuestionOutputParser())