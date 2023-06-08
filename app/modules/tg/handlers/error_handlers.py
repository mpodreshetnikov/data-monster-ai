import logging
from httpx import LocalProtocolError

from telegram.ext import Application, ContextTypes
from telegram import Update

from modules.tg.utils.exceptions import UserNotAllowedException
from modules.tg.utils.texts import message_text_for
from modules.common.errors import get_info_from_exception
from ..utils.statistics_writer import StatisticWriter
from modules.data_access.main import InternalDB

logger = logging.getLogger(__name__)


def add_handlers(application: Application, internal_db: InternalDB):
    application.add_error_handler(
        lambda update, context: __error_handler__(update, context, internal_db),
    )


async def __error_handler__(
    update: Update, context: ContextTypes.DEFAULT_TYPE, internal_db: InternalDB
):
    error = context.error
    user_id = update.effective_user.id if update.effective_user else None
    ray_id = context.user_data["ray_id"]

    await internal_db.request_outcome_repository.add(
        ray_id=ray_id, successful=False, error=error
    )

    if isinstance(error, LocalProtocolError):
        logger.error(error, exc_info=True)
        return

    if isinstance(error, UserNotAllowedException):
        username = update.effective_user.username
        user_id = update.effective_user.id
        method_name = error.method_name or "app"
        logger.info(f"User {username}:{user_id} was not allowed to the {method_name}")
        try:
            await update.message.reply_text(
                message_text_for("user_not_allowed"), parse_mode="HTML"
            )
        except Exception as e:
            logger.error(e, exc_info=True)
        return

    logger.error(error, exc_info=True)
    try:
        if ray_id:
            await update.message.reply_text(
                message_text_for("unknown_error_with_ray_id", ray_id=ray_id),
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                message_text_for("unknown_error"), parse_mode="HTML"
            )
    except Exception as e:
        logger.error(e, exc_info=True)
