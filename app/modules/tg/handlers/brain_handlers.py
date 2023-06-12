import logging
import json
import datetime
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    Application,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from mypy_boto3_s3 import S3Client

from modules.tg.utils.texts import message_text_for
from modules.tg.utils.decorators import a_only_allowed_users
from modules.tg.utils.time_watching import ExecInfoStorage

from modules.brain.main import Brain
from modules.data_access.main import InternalDB
from modules.data_access.models.brain_response_data import BrainResponseData
from ..web_app.main import WebApp, WebAppTypes
from ..utils.button_id import ButtonId

logger = logging.getLogger(__name__)


def add_handlers(
    application: Application,
    brain: Brain,
    internal_db: InternalDB,
    web_app_base_url: str | None = None,
    s3client: S3Client | None = None,
):
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            __get__ask_brain_handler__(brain, web_app_base_url, s3client, internal_db),
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            lambda update, context: show_sql_callback(update, context, internal_db)
        )
    )


def __get__ask_brain_handler__(
    brain: Brain,
    web_app_base_url: str | None = None,
    s3client: S3Client | None = None,
    internal_db: InternalDB | None = None,
):
    if not web_app_base_url:
        logger.warning("No web_app_base_url provided, chart page will not be available")
    if not s3client:
        logger.warning("No s3client provided, chart page will not be available")

    exec_info_storage = ExecInfoStorage(count=10)

    @a_only_allowed_users
    async def __ask_brain_handler__(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id if update.effective_chat else None
        user_id = update.effective_user.id if update.effective_user else None
        message_id = update.effective_message.message_id if update.effective_message else None
        question = (
            " ".join(context.args)
            if context.args
            else update.message.text
            if update.message
            else None
        )

        ray_id = str(uuid.uuid4())
        # comment: what if the bot will also be in group chats and ask questions there? hm.. let's leave todo about that
        context.user_data["ray_id"] = ray_id
        if not chat_id or not user_id or not question or not message_id:
            raise ValueError(
                "Empty chat_id or message_id or user_id or question provided"
            )

        username = update.effective_user.username if update.effective_user else None
        current_time = datetime.datetime.now()
        moscow_tz = datetime.timezone(datetime.timedelta(hours=3))
        current_time_moscow = current_time.astimezone(moscow_tz)
        timestamp = current_time_moscow.strftime("%Y-%m-%d %H:%M:%S")

        try:
            await internal_db.user_request_repository.add(
                ray_id=ray_id, timestamp=timestamp, username=username, user_id=user_id
            )
        except Exception as e:
            logger.error(e, exc_info=True)
            
        logger.info(f"User {username}:{user_id} asked a question {question}")

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

        exec_info_storage_key = f"{chat_id}_{user_id}"
        exec_info_storage.start(exec_info_storage_key)

        answer = await brain.answer(question, ray_id)

        logger.info(
            f"User {username}:{user_id} got brain answer: {str(answer.answer_text)}"
        )

        sql_button = None
        chart_button = None

        if answer.sql_script:
            sql_button = InlineKeyboardButton(
                text=message_text_for("answer_show_sql_button"),
                callback_data=json.dumps(
                    {"id": ButtonId.ID_SQL_BUTTON.value, "ray_id": answer.ray_id}
                ),
            )

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

        keyboard = []
        if sql_button:
            keyboard.append(sql_button)
        if chart_button:
            keyboard.append(chart_button)

        reply_markup = InlineKeyboardMarkup([keyboard])

        exec_info_storage.stop(exec_info_storage_key)

        await context.bot.send_message(
            chat_id,
            message_text_for(
                "answer_with_ray_id", answer=answer.answer_text, ray_id=answer.ray_id
            ),
            parse_mode="HTML",
            reply_markup=reply_markup,
        )

        await context.bot.send_message(
            chat_id, message_text_for("continue_dialog"), parse_mode="HTML"
        )

        try:
            await internal_db.request_outcome_repository.add(
                ray_id=ray_id, successful=True, error=None
            )
        except Exception as e:
            logger.error(e, exc_info=True)

    return __ask_brain_handler__


async def show_sql_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, internal_db: InternalDB
):
    query = update.callback_query
    if not query:
        await update.message.reply_text(message_text_for("not_found_script_error"))
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
    if brain_response_data and brain_response_data.sql_script:
        answer_with_sql = message_text_for(
            "answer_with_sql_script",
            answer=answer_without_sql,
            sql_script=brain_response_data.sql_script,
        )
        await query.edit_message_text(text=answer_with_sql)
    else:
        await query.edit_message_text(
            text=query.message.text + message_text_for("not_found_script_error")
        )
    new_reply_markup = InlineKeyboardMarkup([keyboard_without_sql])
    if new_reply_markup != reply_markup:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([keyboard_without_sql])
        )
