import logging

from telegram.ext import Application, ContextTypes
from telegram import Update

from modules.tg.utils.exceptions import UserNotAllowedException
from modules.tg.utils.texts import message_text_for
from modules.common.errors import (
    get_info_from_exception, AgentLimitExceededAnswerException,
    SQLTimeoutAnswerException, CreatedNotWorkingSQLAnswerException,
    NoDataReturnedFromDBAnswerException, LLMContextExceededAnswerException)

from modules.data_access.main import InternalDB

logger = logging.getLogger(__name__)


def add_handlers(application: Application, internal_db: InternalDB):
    application.add_error_handler(
        lambda update, context: __error_handler__(update, context, internal_db),
    )


async def __error_handler__(update: Update, context: ContextTypes.DEFAULT_TYPE, internal_db: InternalDB):
    # TODO logic not actual anymore, brain errors are cathced inside brain handlers
    error = context.error

    username = update.effective_user.username if update.effective_user else None
    user_id = update.effective_user.id if update.effective_user else None
    ray_id = context.user_data["ray_id"]
    chat_id = update.effective_chat.id if update.effective_chat else None


    effective_message = update.effective_message
    message_id = effective_message.message_id if effective_message else None

    if not effective_message:
        logger.error("Error occured but no effective message found.")
        if error:
            logger.error(error, exc_info=True)
        else:
            logger.error("An unknown error occurred.")
        return

    if not error:
        logger.error("An unknown error occurred.")
        await effective_message.reply_text(message_text_for("unknown_error"), parse_mode="HTML")
        return

    logger.error(error, exc_info=True)

    if isinstance(error, UserNotAllowedException):
        method_name = error.method_name or "app"
        logger.info(f"User {username}:{user_id} was not allowed to the {method_name}")
        try:
            await effective_message.reply_text(message_text_for("user_not_allowed"), parse_mode="HTML")
        except Exception as e:
            logger.error(e, exc_info=True)
        return

    error_message = ""

    if isinstance(error, AgentLimitExceededAnswerException):
        error_message = message_text_for("error_AgentLimitExceededAnswerException")
    if isinstance(error, SQLTimeoutAnswerException):
        error_message = message_text_for("error_SQLTimeoutAnswerException")
    if isinstance(error, CreatedNotWorkingSQLAnswerException):
        error_message = message_text_for("error_CreatedNotWorkingSQLAnswerException")
    if isinstance(error, NoDataReturnedFromDBAnswerException):
        error_message = message_text_for("error_NoDataReturnedFromDBAnswerException")
    if isinstance(error, LLMContextExceededAnswerException):
        error_message = message_text_for("error_LLMContextExceededAnswerException")

    if not error_message:
        error_message = message_text_for("unknown_error")

    if ray_id:
        ray_id_text = message_text_for("ray_id_ext", ray_id=ray_id)
        error_message += ray_id_text

    try:
        await internal_db.request_outcome_repository.add(
            ray_id=ray_id,
            successful=False,
            error=f"{type(error).__name__}: {error_message}",
        )
    except Exception as e:
        logger.error(e, exc_info=True)

    try:
        await effective_message.reply_text(
            error_message,
            parse_mode="HTML")
    except Exception as e:
        logger.error(e, exc_info=True)
