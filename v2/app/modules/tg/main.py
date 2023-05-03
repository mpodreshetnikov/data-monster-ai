import modules.tg.handlers.init_chat_handler as init_chat_handler
from modules.tg.consts.texts import set_config_file_path as set_texts_config_file_path

from telegram.ext import ApplicationBuilder, Application

import logging, os


logger = logging.getLogger(__name__)


def run_bot_and_block_thread(token: str):
    application = __setup_application__(token)
    logger.info("Running telegram bot...")
    application.run_polling()


async def start_bot(token: str):
    application = __setup_application__(token)
    
    logger.info("Starting telegram bot...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logger.info("Telegram bot started")
    
    return application


async def stop_bot(application: Application):
    logger.info("Stopping telegram bot...")
    await application.updater.stop()
    await application.stop()
    await application.shutdown()
    logger.info("Telegram bot stopped")
    

def __setup_application__(token: str) -> Application:
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))
    
    debugMode = bool(os.getenv("DEBUG", False))
    application = ApplicationBuilder().token(token).concurrent_updates(True).build()
    
    set_texts_config_file_path(os.path.join(__location__, "tg_texts.json"))
    
    # Handlers, required order
    init_chat_handler.add_handler(application)
    application.add_error_handler(lambda _, context: logger.error(context.error, exc_info=True))
    
    return application