import dbaccess, prompts, ai
from enum import Enum
import pandas as pd

class AnswerType(Enum):
    ERROR = 0
    NUMBER = 1
    TABLE = 2
    PLOT = 3

def answer(question: str):
    db_schema = dbaccess.get_db_schema_via_sql()
    prompt = prompts.prepare_prompt(db_schema, question)
    ai_db_request = ai.generate_db_request(prompt)
    db_response_df = dbaccess.do_db_request(ai_db_request)
    return (db_response_df, ai_db_request, type_of_answer(db_response_df))

def type_of_answer(db_response_df):
    match db_response_df:
        case str(db_response_df):
            return AnswerType.ERROR
        case pd.DataFrame(size=1):
            return AnswerType.NUMBER
        case _:
            return AnswerType.TABLE