import logging
from httpx import LocalProtocolError

from telegram.ext import Application, ContextTypes
from telegram import Update

from modules.tg.utils.exceptions import UserNotAllowedException
from modules.tg.utils.texts import message_text_for
from modules.common.errors import get_info_from_exception
from ..utils.statistics_writer import StatisticWriter 

logger = logging.getLogger(__name__)


def add_handlers(application: Application, statistic):
    application.add_error_handler(lambda update, context: __error_handler__(update, context, statistic),)
    

async def __error_handler__(update: Update, context: ContextTypes.DEFAULT_TYPE, statistic:str):
    error = context.error
    ray_id = get_info_from_exception(error, "ray_id")
    user_id = update.effective_user.id if update.effective_user else None
    message_id = update.message.message_id if update.effective_message else None
    chat_id = update.effective_chat.id if update.effective_chat else None

    if chat_id and message_id:
            StatisticWriter.false_successful(statistic, chat_id, message_id, error)
        
    if (isinstance(error, LocalProtocolError)):
        logger.error(error, exc_info=True)
        return

    if isinstance(error, UserNotAllowedException):
        username = update.effective_user.username
        user_id = update.effective_user.id
        method_name = error.method_name or "app"
        logger.info(f"User {username}:{user_id} was not allowed to the {method_name}")
        try:
            await update.message.reply_text(message_text_for("user_not_allowed"), parse_mode="HTML")
        except Exception as e:
            logger.error(e, exc_info=True)
        return
    
    logger.error(error, exc_info=True)
    try:
        if ray_id:
            await update.message.reply_text(message_text_for("unknown_error_with_ray_id", ray_id=ray_id), parse_mode="HTML")
        else:
            await update.message.reply_text(message_text_for("unknown_error"), parse_mode="HTML")
    except Exception as e:
        logger.error(e, exc_info=True)
        

    