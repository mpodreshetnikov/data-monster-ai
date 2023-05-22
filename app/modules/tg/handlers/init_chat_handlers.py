import logging

from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

from modules.tg.utils.texts import message_text_for
from modules.tg.utils.decorators import a_only_allowed_users

logger = logging.getLogger(__name__)


def add_handlers(application: Application):
    application.add_handler(CommandHandler("start", __chat_started_handler__))


@a_only_allowed_users
async def __chat_started_handler__(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_name = update.effective_user.name
    logger.info(f"User {user_name}:{update.effective_user.id} started a chat")
    await context.bot.send_message(chat_id, message_text_for("hello", name=user_name), parse_mode="HTML")