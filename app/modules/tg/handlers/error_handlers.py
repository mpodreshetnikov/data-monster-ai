import logging

from telegram.ext import Application, ContextTypes
from telegram import Update

from modules.tg.utils.exceptions import UserNotAllowedException
from modules.tg.utils.texts import message_text_for
from modules.common.errors import (
    get_info_from_exception, AgentLimitExceededAnswerException,
    SQLTimeoutAnswerException, CreatedNotWorkingSQLAnswerException,
    NoDataReturnedFromDBAnswerException)
from ..utils.statistics_writer import StatisticWriter 

logger = logging.getLogger(__name__)


def add_handlers(application: Application, statistic):
    application.add_error_handler(lambda update, context: __error_handler__(update, context, statistic),)
    

async def __error_handler__(update: Update, context: ContextTypes.DEFAULT_TYPE, statistic: str):
    error = context.error

    username = update.effective_user.username if update.effective_user else None
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None

    effective_message = update.effective_message
    message_id = effective_message.message_id if effective_message else None

    StatisticWriter.false_successful(
        statistic, str(chat_id), str(message_id), str(error or "unknown error"))

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

    ray_id = get_info_from_exception(error, "ray_id")

    if isinstance(error, UserNotAllowedException):
        method_name = error.method_name or "app"
        logger.info(f"User {username}:{user_id} was not allowed to the {method_name}")
        try:
            await effective_message.reply_text(message_text_for("user_not_allowed"), parse_mode="HTML")
        except Exception as e:
            logger.error(e, exc_info=True)
        return

    if isinstance(error, AgentLimitExceededAnswerException):
        pass # TODO: add handler for this exception

    if isinstance(error, SQLTimeoutAnswerException):
        pass # TODO: add handler for this exception

    if isinstance(error, CreatedNotWorkingSQLAnswerException):
        pass # TODO: add handler for this exception

    if isinstance(error, NoDataReturnedFromDBAnswerException):
        pass # TODO: add handler for this exception
    
    logger.error(error, exc_info=True)
    try:
        if ray_id:
            await effective_message.reply_text(
                message_text_for("unknown_error_with_ray_id", ray_id=ray_id),
                parse_mode="HTML")
        else:
            await effective_message.reply_text(
                message_text_for("unknown_error"),
                parse_mode="HTML")
    except Exception as e:
        logger.error(e, exc_info=True)
        

    