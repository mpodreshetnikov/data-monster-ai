from telegram import Update
from telegram.ext import ContextTypes


def get_params(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> tuple[int, int, str, int, str, dict]:
    """
    Get params from update and context:
    chat_id, user_id, username, message_id, text, user_data
    """
    chat_id = update.effective_chat.id if update.effective_chat else None
    user_id = update.effective_user.id if update.effective_user else None
    username = update.effective_user.username if update.effective_user else None
    message_id = update.effective_message.message_id if update.effective_message else None
    text = (
        " ".join(context.args)
        if context.args
        else update.message.text
        if update.message
        else None
    )

    user_data = context.user_data
    if user_data is None:
        raise ValueError("No context.user_data provided")
    
    if not chat_id or not user_id or not username or not message_id or not text:
        raise ValueError(
            "Empty chat_id or message_id or user_id or message text provided"
        )

    return (chat_id, user_id, username, message_id, text, user_data)
