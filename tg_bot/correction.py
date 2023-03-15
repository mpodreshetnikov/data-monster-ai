from enum import Enum
from telegram import constants, Update
from telegram.ext import ContextTypes, Application, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from dbaccess import DbAccess
from my_types import ButtonMenuActions
import logging, json


logger = logging.getLogger(__name__)


class Correction():
    question: str
    answer: str

    def __init__(self, question: str, answer: str) -> None:
        self.question = question
        self.answer = answer


class States(Enum):
    WAITING_CORRECTION = 1


class CorrectionDbAccess(DbAccess):
    def __init__(self, db_config_section_name: str) -> None:
        super().__init__(db_config_section_name)
        with self.db_conn.cursor() as cur:
            cur.execute("""
CREATE TABLE IF NOT EXISTS corrections (
    id uuid,
    question text NOT NULL,
    answer text NOT NULL,
    CONSTRAINT corrections_id PRIMARY KEY(id)
);""")
        self.db_conn.commit()


    def add_correction(self, correction: Correction) -> None:
        with self.db_conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM corrections WHERE question = '{correction.question}';")
            response = cur.fetchall()
            if response[0][0] > 0: return
            cur.execute(
                "INSERT INTO corrections VALUES (gen_random_uuid(), %(question)s, %(answer)s);",
                { 'question': correction.question, 'answer': correction.answer })
        self.db_conn.commit()
        logger.info(f"Added correction for question: {correction.question}")

    
    def get_good_corrections(self, question: str, limit: int) -> list[str]:
        with self.db_conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            cur.execute("""
SELECT question, answer
FROM corrections
WHERE similarity(question, %(question)s) > 0
ORDER BY similarity(question, %(question)s) DESC
LIMIT %(limit)s
""", { 'question': question, 'limit': limit })
            response = cur.fetchall()
            good_corrections = list(map(lambda x: Correction(x[0], x[1]), response))
            logger.info(f"For question '{question}' following corrections returned:")
            logger.info(json.dumps(list(map(lambda x: x.question, good_corrections))))
            return good_corrections


def add_correction_handler(application: Application) -> None:
    application.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(__start_button_callback__, pattern=ButtonMenuActions.CORRECT_ANSWER)],
        states={
            States.WAITING_CORRECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, __correction_sent_callback__)
            ]
        },
        fallbacks=[MessageHandler(filters.ALL, __cancel_correction__)]
    ))


# just pressed correct button: send text asking right answer
async def __start_button_callback__(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Started correction")
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    last_question = context.user_data.get('last_question')
    logger.info(f"For question {last_question}")

    await context.bot.send_message(
        chat_id,
        text=f"Отправьте правильный вариант кода для запроса: <b>{last_question}</b>",
        parse_mode=constants.ParseMode.HTML)
    logger.info(f"Waiting for correction...")
    return States.WAITING_CORRECTION


# check and setup correction
async def __correction_sent_callback__(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    last_question = context.user_data.get('last_question')
    correction = " ".join(context.args) if context.args else update.message.text

    dbaccess = CorrectionDbAccess("corrections_db")
    dbaccess.add_correction(Correction(last_question, correction))

    await context.bot.send_message(chat_id, text="Корректировка успешно применена")
    return ConversationHandler.END


async def __cancel_correction__(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Canceled correction")
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, text="Корректировка ответа отменена")
    return ConversationHandler.END