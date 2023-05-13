from telegram import Update

from modules.security.main import is_user_allowed
from exceptions import UserNotAllowedException
from texts import message_text_for

def only_allowed_users(func):
    async def wrapper(*args, **kwargs):
        update: Update = kwargs.get('update')
        if not update or not isinstance(update, Update):
            return await func(*args, **kwargs)
        
        # Try to check by id
        tg_user_id = update.effective_user.id
        if is_user_allowed(tg_user_id):
            return await func(*args, **kwargs)
        
        # Try to check by username
        tg_username = update.effective_user.username
        if is_user_allowed(tg_username):
            return await func(*args, **kwargs)
        
        await update.message.reply_text(message_text_for("user_not_allowed"))
        raise UserNotAllowedException()
    return wrapper