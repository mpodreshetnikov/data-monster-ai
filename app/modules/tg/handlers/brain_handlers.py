from enum import Enum
import logging
import json
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    Application,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from mypy_boto3_s3 import S3Client

from modules.tg.utils.texts import message_text_for
from modules.tg.utils.decorators import a_only_allowed_users
from modules.tg.utils.time_watching import ExecInfoStorage

from modules.brain.main import Brain, BrainMode, Answer
from modules.data_access.main import InternalDB
from modules.common.errors import AgentLimitExceededAnswerException
from modules.tg.utils.tg_params_helpers import get_params
from modules.common.helpers import a_exec_no_raise
from ..web_app.main import WebApp, WebAppTypes
from ..utils.buttons import ButtonId, build_keybord

logger = logging.getLogger(__name__)


class ConversationStates(Enum):
    WAITING_FOR_CLARIFYING_ANSWER = 1

def add_handlers(
    application: Application,
    brain: Brain,
    internal_db: InternalDB,
    web_app_base_url: str | None = None,
    s3client: S3Client | None = None,
):
    application.add_handler(
        CallbackQueryHandler(
            lambda update, context: show_sql_callback(update, context, internal_db),
            block=False,
        )
    )

    # TODO implement exception handling during conversation https://github.com/python-telegram-bot/python-telegram-bot/issues/2277#issuecomment-757501019
    application.add_handler(ConversationHandler(
        entry_points=[MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            __get__ask_brain_handler(brain, web_app_base_url, s3client, internal_db))],
        states={
            ConversationStates.WAITING_FOR_CLARIFYING_ANSWER: [
                # TODO implement method for clarifying question. in it we need to get all data and send it to brain to answer again
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                    __get__ask_brain_with_clarifying_answer(brain, web_app_base_url, s3client, internal_db))
            ],
        },
        fallbacks=[MessageHandler(filters.ALL, __default_fallback)],
        per_user=True,
        per_chat=True,
    ))


def __create_chart_and_get_chart_button(
    answer: Answer,
    web_app_base_url: str | None,
    s3client: S3Client | None,
) -> InlineKeyboardButton | None:
    chart_button = None
    if answer.chart_params and web_app_base_url and s3client:
        try:
            web_app = WebApp(WebAppTypes.CHART_PAGE, web_app_base_url, s3client)
            page_url = web_app.create_and_save(answer)
            chart_button = InlineKeyboardButton(
                text=message_text_for("answer_open_chart_button"),
                web_app=WebAppInfo(url=page_url),
            )
        except Exception as e:
            logger.error("failed to create_and_save", str(e), exc_info=True)
            chart_button = None
    return chart_button


def __get_sql_script_button(answer: Answer) -> InlineKeyboardButton | None:
    if answer.sql_script:
        return InlineKeyboardButton(
            text=message_text_for("answer_show_sql_button"),
            callback_data=json.dumps(
                {"id": ButtonId.ID_SQL_BUTTON.value, "ray_id": answer.ray_id}
            ),
        )
    return None


async def __send_user_awaiting_for_answer_message(
        chat_id: int, exec_info_storage: ExecInfoStorage, context: ContextTypes.DEFAULT_TYPE):
    seconds = None
    if exec_info_storage:
        seconds = exec_info_storage.average()
    if seconds:
        await context.bot.send_message(
            chat_id,
            message_text_for("brain_thinking_with_time", seconds=seconds),
            parse_mode="HTML",
        )
    else:
        await context.bot.send_message(
            chat_id, message_text_for("brain_thinking"), parse_mode="HTML"
        )


async def __send_answer(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    answer: Answer,
    reply_markup: InlineKeyboardMarkup | None = None,
):
    await context.bot.send_message(
        chat_id,
        message_text_for(
            "answer_with_ray_id", answer=answer.answer_text, ray_id=answer.ray_id
        ),
        parse_mode="HTML",
        reply_markup=reply_markup, # type: ignore
    )

    await context.bot.send_message(
        chat_id, message_text_for("continue_dialog"), parse_mode="HTML"
    )


def __get__ask_brain_with_clarifying_answer(
    brain: Brain,
    web_app_base_url: str | None = None,
    s3client: S3Client | None = None,
    internal_db: InternalDB | None = None,
):
    if not web_app_base_url:
        logger.warning("No web_app_base_url provided, chart page will not be available")
    if not s3client:
        logger.warning("No s3client provided, chart page will not be available")
    if not internal_db:
        raise ValueError("No internal_db provided")

    exec_info_storage = ExecInfoStorage(count=10)

    @a_only_allowed_users
    async def __ask_brain_handler_with_clarifying_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id, user_id, username, _, user_answer, user_data = get_params(update, context)

        ray_id = user_data.get("ray_id")
        if not ray_id:
            raise ValueError(
                f"No ray_id in user_data while clarifying answer, cannot process the request correctly. tg_user_id: {user_id}")
        initial_question = await internal_db.user_request_repository.get(ray_id)
        if not initial_question:
            raise ValueError(
                f"No initial question in db while clarifying answer, cannot process the request correctly. tg_user_id: {user_id}")
        clarifying_question = await internal_db.brain_response_repository.get_last_clarifying_question(ray_id)
        if not clarifying_question:
            raise ValueError(
                f"No clarifying question in db while clarifying answer, cannot process the request correctly. tg_user_id: {user_id}")

        question = f"{initial_question}\n{clarifying_question}\n{user_answer}"
            
        logger.info(f"User {username}:{user_id} asked a question with clarifying {question}")

        await __send_user_awaiting_for_answer_message(chat_id, exec_info_storage, context)

        exec_info_storage.start(ray_id)

        # IMPORTANT, here we use not SHORT but DEFAULT mode.
        answer = await brain.answer(question, ray_id, mode=BrainMode.DEFAULT)
        if not answer:
            raise ValueError(f"Empty answer. ray_id: {ray_id}.")
        logger.info(
            f"User {username}:{user_id} got brain answer: {str(answer.answer_text)}"
        )

        sql_button = __get_sql_script_button(answer)
        chart_button = __create_chart_and_get_chart_button(answer, web_app_base_url, s3client)

        exec_info_storage.stop(ray_id)

        reply_markup = build_keybord(InlineKeyboardMarkup, [sql_button, chart_button], columns=2)
        await __send_answer(chat_id, context, answer, reply_markup)

        await a_exec_no_raise(
            internal_db.request_outcome_repository.add(
                ray_id=ray_id, successful=True, error=None
        ))

        return ConversationHandler.END

    return __ask_brain_handler_with_clarifying_answer


def __get__ask_brain_handler(
    brain: Brain,
    web_app_base_url: str | None = None,
    s3client: S3Client | None = None,
    internal_db: InternalDB | None = None,
):
    if not web_app_base_url:
        logger.warning("No web_app_base_url provided, chart page will not be available")
    if not s3client:
        logger.warning("No s3client provided, chart page will not be available")
    if not internal_db:
        raise ValueError("No internal_db provided")

    exec_info_storage = ExecInfoStorage(count=10)

    @a_only_allowed_users
    async def __ask_brain_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id, user_id, username, _, question, user_data = get_params(update, context)

        ray_id = str(uuid.uuid4())
        # comment: what if the bot will also be in group chats and ask questions there? hm.. let's leave todo about that
        user_data["ray_id"] = ray_id

        await a_exec_no_raise(
            internal_db.user_request_repository.add(
                ray_id=ray_id, username=username or "", user_id=user_id
        ))
            
        logger.info(f"User {username}:{user_id} asked a question {question}")

        await __send_user_awaiting_for_answer_message(chat_id, exec_info_storage, context)

        exec_info_storage.start(ray_id)

        answer = None
        try:
            answer = await brain.answer(question, ray_id, mode=BrainMode.SHORT)
        # Once catch agent limit exception and do clarifing question or restart the brain
        except AgentLimitExceededAnswerException as _e:
            # TODO write statistics correctly ???
            # TODO refactor this
            if not _e.agent_work_text:
                raise _e

            clarifying_question = await a_exec_no_raise(
                brain.make_clarifying_question(_e.agent_work_text, ray_id)
            )
            if (
                not clarifying_question
                or clarifying_question.action == clarifying_question.Action.Restart
                or not clarifying_question.clarifying_question
            ):
                logger.info(f"No clarifying question was generated. ray_id: {ray_id}. Restarting the brain answering...")
                answer = await brain.answer(question, ray_id, mode=BrainMode.DEFAULT)
            else:
                await context.bot.send_message(
                    chat_id,
                    clarifying_question.clarifying_question,
                )
                return ConversationStates.WAITING_FOR_CLARIFYING_ANSWER

        if not answer:
            raise ValueError(f"Empty answer. ray_id: {ray_id}.")
        logger.info(
            f"User {username}:{user_id} got brain answer: {str(answer.answer_text)}"
        )

        sql_button = __get_sql_script_button(answer)
        chart_button = __create_chart_and_get_chart_button(answer, web_app_base_url, s3client)

        exec_info_storage.stop(ray_id)

        reply_markup = build_keybord(InlineKeyboardMarkup, [sql_button, chart_button], columns=2)
        await __send_answer(chat_id, context, answer, reply_markup)

        await a_exec_no_raise(
            internal_db.request_outcome_repository.add(
                ray_id=ray_id, successful=True, error=None
            )
        )

    return __ask_brain_handler


async def show_sql_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, internal_db: InternalDB
):
    query = update.callback_query
    await query.answer()
    answer_without_sql = query.message.text
    callback_data = json.loads(query.data)
    ray_id = callback_data["ray_id"]

    brain_response_data = await internal_db.brain_response_repository.get(ray_id = ray_id)
    reply_markup = query.message.reply_markup
    keyboard_without_sql = []
    for button_row in reply_markup.inline_keyboard:
        for button in button_row:
            if not button.callback_data:
                keyboard_without_sql.append(button)
            elif (
                json.loads(button.callback_data)["id"]
                != ButtonId.ID_SQL_BUTTON.value
            ):
                keyboard_without_sql.append(button)
    new_reply_markup = InlineKeyboardMarkup([keyboard_without_sql])           
    if new_reply_markup != reply_markup:
        reply_markup = new_reply_markup
    if brain_response_data and brain_response_data.sql_script:
        answer_with_sql = message_text_for(
            "answer_with_sql_script",
            answer=answer_without_sql,
            sql_script=brain_response_data.sql_script,
        )
        await query.edit_message_text(text=answer_with_sql, reply_markup = reply_markup)
    else:
        await query.edit_message_text(
            text=query.message.text + message_text_for("not_found_script_error"),reply_markup = reply_markup
        )
