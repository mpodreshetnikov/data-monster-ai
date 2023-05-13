import logging
from telegram import Update

from modules.security.main import is_user_allowed
from modules.tg.helpers.exceptions import UserNotAllowedException


logger = logging.getLogger(__name__)


def only_allowed_users(func):
    async def wrapper(*args, **kwargs):
        update: Update = next(filter(lambda t: isinstance(t, Update), args), None)
        if not update:
            logger.error("User access cannot be checked. <Update> not found in args", exc_info=True)
            raise UserNotAllowedException(method_name=func.__name__)
        
        # Try to check by id
        tg_user_id = update.effective_user.id
        if is_user_allowed(tg_user_id):
            return await func(*args, **kwargs)
        
        # Try to check by username
        tg_username = update.effective_user.username
        if is_user_allowed(tg_username):
            return await func(*args, **kwargs)
        
        raise UserNotAllowedException(method_name=func.__name__)
    
    return wrapper