import logging

from telegram.ext import Application, ContextTypes
from telegram import Update

from modules.tg.utils.exceptions import UserNotAllowedException
from modules.tg.utils.texts import message_text_for


logger = logging.getLogger(__name__)


def add_handlers(application: Application):
    application.add_error_handler(__error_handler__)
    
    
async def __error_handler__(update: Update, context: ContextTypes.DEFAULT_TYPE):
    error = context.error

    if isinstance(error, UserNotAllowedException):
        username = update.effective_user.username
        user_id = update.effective_user.id
        method_name = error.method_name or "app"
        logger.info(f"User {username}:{user_id} was not allowed to the {method_name}")
        try:
            await update.message.reply_text(message_text_for("user_not_allowed"))
        except Exception as e:
            logger.error(e, exc_info=True)
        return
    
    logger.error(error, exc_info=True)
    try:
        await update.message.reply_text(message_text_for("unknown_error"))
    except Exception as e:
        logger.error(e, exc_info=True)
    
    