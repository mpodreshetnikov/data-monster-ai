from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

from modules.tg.consts.texts import get_message_text


def add_handler(application: Application):
    application.add_handler(CommandHandler("start", __chat_started_handler__))


async def __chat_started_handler__(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=get_message_text("hello"))