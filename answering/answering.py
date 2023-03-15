from my_types import Answer, AnswerType
import prompts, ai
from dbaccess import DbAccess
import pandas as pd
from tg_bot.correction import CorrectionDbAccess
import logging, json

logger = logging.getLogger(__name__)

def answer(question: str):
    dbaccess = DbAccess("db")
    db_schema = dbaccess.get_db_schema_via_sql()

    corr_dbaccess = CorrectionDbAccess("corrections_db")
    examples = corr_dbaccess.get_good_corrections(question, 3)
    logger.info(f"Got {len(examples)} examples for prompt")

    prompt = prompts.prepare_prompt(db_schema, question, examples)
    logger.info(f"Prompt builded")

    logger.info(f"Generation AI answers")
    ai_db_requests = ai.generate_answer_code(prompt)
    logger.info(f"{len(ai_db_requests)} AI answers generated")

    answer = dbaccess.try_db_requests(ai_db_requests)
    logger.info(f"Answer generated")
    logger.info(json.dumps(answer))
    if answer.type == None:
        try_set_type_of_answer(answer)
        logger.info(f"Answer type changed to {answer.type}")
    
    return answer


def try_set_type_of_answer(answer: Answer) -> None:
    match answer.answer_result:
        case pd.DataFrame(size=1):
            answer.type = AnswerType.NUMBER
        case _:
            answer.type = AnswerType.TABLE