from telegram.ext import Application, MessageHandler, ContextTypes, filters
from telegram import Update

from modules.tg.utils.texts import message_text_for
from modules.tg.utils.decorators import only_allowed_users

from modules.brain.main import Brain


def add_handlers(application: Application, brain: Brain):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, __get__ask_brain_handler__(brain)))

def __get__ask_brain_handler__(brain: Brain) -> None:
    
    @only_allowed_users
    async def __ask_brain_handler__(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        question = " ".join(context.args) if context.args else update.message.text

        await context.bot.send_message(chat_id, message_text_for("brain_thinking"))

        answer = brain.answer_question(question)

        await context.bot.send_message(chat_id, answer)
        await context.bot.send_message(chat_id, message_text_for("continue_dialog"))
        
    return __ask_brain_handler__