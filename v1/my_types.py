from enum import Enum
from pandas import DataFrame
from matplotlib.figure import Figure

class AnswerType(str, Enum):
    NO_DATA = 'NO_DATA'
    NUMBER = 'NUMBER'
    TABLE = 'TABLE'
    PLOT = 'PLOT'

class Interaction:
    question: str
    answer_result: DataFrame | None
    answer_code: str
    answer_type: AnswerType | None
    figure: Figure | None
    figure_code: str

    def __init__(self, question: str):
        self.question = question
        self.answer_result = None
        self.answer_code = ""
        self.answer_type = None
        self.figure = None
        self.figure_code = ""
    
    def set_answer(self, answer_result: DataFrame | None, answer_code: str = "", type: AnswerType = None) -> None:
        self.answer_result = answer_result
        self.answer_code = answer_code
        self.answer_type = type

    def set_figure(self, figure: Figure | None, figure_code: str = "") -> None:
        self.figure = figure
        self.figure_code = figure_code

    def __json__(self):
        return self.__dict__


class ButtonMenuActions(str, Enum):
    CORRECT_ANSWER = 'CORRECT_ANSWER'