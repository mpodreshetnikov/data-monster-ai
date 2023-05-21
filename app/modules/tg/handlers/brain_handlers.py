import logging

from telegram.ext import Application, MessageHandler, ContextTypes, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo

from modules.tg.utils.texts import message_text_for
from modules.tg.utils.decorators import a_only_allowed_users
from modules.tg.utils.time_watching import ExecInfoStorage

from modules.brain.main import Brain

from ..web_app.main import WebApp, WebAppTypes


logger = logging.getLogger(__name__)


def add_handlers(application: Application, brain: Brain, web_app_base_url: str):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, __get__ask_brain_handler__(brain, web_app_base_url)))


def __get__ask_brain_handler__(brain: Brain, web_app_base_url: str) -> None:
    if not web_app_base_url:
        logger.warning("No web_app_base_url provided, chart page will not be available")

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
        # --- START OF ANSWERING BODY

        answer = brain.answer(question)
        logger.info(f"User {update.effective_user.username}:{update.effective_user.id} got brain answer: {str(answer.answer_text)}")
        
        if answer.chart_code and web_app_base_url:
            web_app = WebApp(WebAppTypes.ChartPage, web_app_base_url)
            page_url = web_app.create_and_save(question=answer.question, js_code_insertion=answer.chart_code)
            web_app_button = InlineKeyboardButton(
                text=message_text_for("answer_open_chart_button"),
                web_app=WebAppInfo(url=page_url),
            )

        # --- END OF ANSWERING BODY
        exec_info_storage.stop(exec_info_storage_key)
        
        await context.bot.send_message(chat_id,
                                       message_text_for("answer_with_ray_id", answer=answer.answer_text, ray_id=answer.ray_id),
                                       parse_mode="HTML",
                                       reply_markup=InlineKeyboardMarkup.from_button(web_app_button) if answer.chart_code else None)
        await context.bot.send_message(chat_id, message_text_for("continue_dialog"), parse_mode="HTML")
        
    return __ask_brain_handler__