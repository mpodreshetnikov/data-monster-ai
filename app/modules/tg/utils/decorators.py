import logging
from functools import wraps

from modules.tg.utils.time_watching import ExecInfoStorage


logger = logging.getLogger(__name__)


def a_only_allowed_users(func):
    from telegram import Update
    from modules.security.main import is_user_allowed
    from modules.tg.utils.exceptions import UserNotAllowedException
    
    @wraps(func)
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


def a_time_watcher(storage: ExecInfoStorage):
    def inner(func):
        if not storage:
            logger.warning(f"Storage is not provided for func {func.__name__}. Time watcher will not work.")
            return func
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            storage.start(func.__name__)
            result = await func(*args, **kwargs)
            storage.stop(func.__name__)
            return result

        return wrapper
    return inner