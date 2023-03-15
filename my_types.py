from enum import Enum
from pandas import DataFrame

class AnswerType(str, Enum):
    NO_DATA = 'NO_DATA'
    NUMBER = 'NUMBER'
    TABLE = 'TABLE'
    PLOT = 'PLOT'

class Answer:
    answer_result: DataFrame | None
    answer_code: str
    type: AnswerType | None

    def __init__(self, answer_result: DataFrame | None, answer_code: str = "", type: AnswerType = None) -> None:
        self.answer_result = answer_result
        self.answer_code = answer_code
        self.type = type
    
    def __json__(self):
        return self.__dict__

class ButtonMenuActions(str, Enum):
    CORRECT_ANSWER = 'CORRECT_ANSWER'