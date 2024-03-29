from mypy_boto3_s3 import S3Client
import modules.tg.handlers.init_chat_handlers as init_chat_handler
import modules.tg.handlers.brain_handlers as brain_handlers
import modules.tg.handlers.error_handlers as error_handlers

from modules.tg.utils.texts import set_config_file_path as set_texts_config_file_path
from modules.common.security import set_users_white_list
from modules.brain.main import Brain
from modules.data_access.main import InternalDB
from telegram.ext import ApplicationBuilder, Application

import logging
import os


logger = logging.getLogger(__name__)


def run_bot_and_block_thread(
    token: str,
    brain: Brain,
    internal_db: InternalDB,
    users_whitelist: list[str] | None = None,
    web_app_base_url: str | None = None,
    s3client: S3Client | None = None,
):
    application = __setup_application__(
        token, brain, internal_db, users_whitelist, web_app_base_url, s3client
    )
    logger.info("Running telegram bot...")
    application.run_polling()


def __setup_application__(
    token: str,
    brain: Brain,
    internal_db: InternalDB,
    users_whitelist: list[str] | None = None,
    web_app_base_url: str | None = None,
    s3client: S3Client | None = None,
) -> Application:
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__))
    )

    application = ApplicationBuilder().token(token).build()

    set_texts_config_file_path(os.path.join(__location__, "tg_texts.json"))
    if users_whitelist:
        set_users_white_list(users_whitelist)

    # Handlers, required order
    init_chat_handler.add_handlers(application)
    brain_handlers.add_handlers(
        application, brain, internal_db, web_app_base_url, s3client
    )
    error_handlers.add_handlers(application, internal_db)

    return application
