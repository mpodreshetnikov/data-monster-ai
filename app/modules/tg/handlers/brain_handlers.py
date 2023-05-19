import logging

from telegram.ext import Application, MessageHandler, ContextTypes, filters
from telegram import Update

from modules.tg.utils.texts import message_text_for
from modules.tg.utils.decorators import a_only_allowed_users
from modules.tg.utils.time_watching import ExecInfoStorage

from modules.brain.main import Brain

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

logger = logging.getLogger(__name__)


def add_handlers(application: Application, brain: Brain):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, __get__ask_brain_handler__(brain)))
    

def __get__ask_brain_handler__(brain: Brain) -> None:
    exec_info_storage = ExecInfoStorage(count=10)
    
    @a_only_allowed_users
    async def __ask_brain_handler__(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        question = " ".join(context.args) if context.args else update.message.text
        
        logger.info(f"User {update.effective_user.username}:{update.effective_user.id} asked a question {question}")

        if exec_info_storage:
            seconds = exec_info_storage.average()
        if seconds:
            await context.bot.send_message(chat_id, message_text_for("brain_thinking_with_time", seconds=seconds), parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id, message_text_for("brain_thinking"), parse_mode="HTML")

        exec_info_storage_key = f"{chat_id}_{user_id}"
        exec_info_storage.start(exec_info_storage_key)

        answer = brain.answer(question)
        ray_id=answer.ray_id
        logger.info(f"User {update.effective_user.username}:{update.effective_user.id} got brain answer: {str(answer.text)}")
          
        
        exec_info_storage.stop(exec_info_storage_key)
        
        keyboard = [[InlineKeyboardButton("SQL", callback_data=f'sql:{ray_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message_text_for("answer_with_ray_id", answer=answer.text, ray_id=ray_id), parse_mode="HTML",  reply_markup=reply_markup)
        
        
        await context.bot.send_message(chat_id, message_text_for("continue_dialog"), parse_mode="HTML")
        
    return __ask_brain_handler__