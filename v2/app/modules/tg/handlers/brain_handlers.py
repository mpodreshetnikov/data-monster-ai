from telegram.ext import Application, MessageHandler, ContextTypes, filters
from telegram import Update

from modules.tg.helpers.texts import message_text_for
from modules.tg.helpers.decorators import only_allowed_users

from modules.brain.main import Brain


def add_handlers(application: Application):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, __ask_brain_handler__))


@only_allowed_users
async def __ask_brain_handler__(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    question = " ".join(context.args) if context.args else update.message.text

    answer = Brain().answer_text_question(question)

    await context.bot.send_message(chat_id, answer)
    await context.bot.send_message(chat_id, message_text_for("continue_dialog"))