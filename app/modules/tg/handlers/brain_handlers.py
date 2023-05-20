import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update

from telegram.ext import Application, MessageHandler, CallbackQueryHandler, ContextTypes, filters


from modules.tg.utils.texts import message_text_for
from modules.tg.utils.decorators import a_only_allowed_users
from modules.tg.utils.time_watching import ExecInfoStorage

from modules.brain.main import Brain

from modules.data_access.main import Engine
from modules.data_access.models.brain_response_data import BrainResponseData


logger = logging.getLogger(__name__)

SQL_CALLBACK_PATTERN = 'sql'


def add_handlers(application: Application, brain: Brain, engine: Engine):
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, __get__ask_brain_handler__(brain)))

    application.add_handler(CallbackQueryHandler(
        lambda update, context: sql_button(update, context, engine), pattern=SQL_CALLBACK_PATTERN))


def __get__ask_brain_handler__(brain: Brain) -> None:
    exec_info_storage = ExecInfoStorage(count=10)

    @a_only_allowed_users
    async def __ask_brain_handler__(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        question = " ".join(
            context.args) if context.args else update.message.text

        logger.info(
            f"User {update.effective_user.username}:{update.effective_user.id} asked a question {question}")

        if exec_info_storage:
            seconds = exec_info_storage.average()
        if seconds:
            await context.bot.send_message(chat_id, message_text_for("brain_thinking_with_time", seconds=seconds), parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id, message_text_for("brain_thinking"), parse_mode="HTML")

        exec_info_storage_key = f"{chat_id}_{user_id}"
        exec_info_storage.start(exec_info_storage_key)

        answer = brain.answer(question)

        logger.info(
            f"User {update.effective_user.username}:{update.effective_user.id} got brain answer: {str(answer.text)}")

        exec_info_storage.stop(exec_info_storage_key)

        if answer.sql_script == None:
            pass
        else:
            keyboard = [[InlineKeyboardButton(
                "SQL", callback_data=f'{SQL_CALLBACK_PATTERN}:{answer.ray_id}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(chat_id, message_text_for("answer_with_ray_id", answer=answer.text, ray_id=answer.ray_id), parse_mode="HTML",  reply_markup=reply_markup)
        await context.bot.send_message(chat_id, message_text_for("continue_dialog"), parse_mode="HTML")

    return __ask_brain_handler__


async def sql_button(update: Update, context: ContextTypes.DEFAULT_TYPE, engine: Engine):
    chat_id = update.effective_chat.id
    query = update.callback_query
    answer_without_sql = query.message.text
    callback_data = query.data
    _, ray_id = callback_data.split(":")

    with engine.Session() as session:
        brain_response_data = session.query(
            BrainResponseData).filter_by(ray_id=ray_id).first()
    if brain_response_data:
        answer_with_sql = answer_without_sql + brain_response_data.sql_script
        await query.edit_message_text(text=answer_with_sql)
        await query.edit_message_reply_markup(reply_markup=None)
    else:
        error_message = "Произошла ошибка и sql-запрос к сожалению утерян"
        await context.bot.send_message(chat_id, error_message)
        await query.edit_message_reply_markup(reply_markup=None)
