import matplotlib.pyplot as plt
import io
import traceback
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.ext import CallbackQueryHandler
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

from modules.brain.main import Brain

from modules.localdb.service_sql import SQLService 

def add_handlers(application: Application):
    application.add_handler(CallbackQueryHandler(sql_button, pattern='sql'))
    
    
async def sql_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    query = update.callback_query
    
    sql_service = SQLService()
    
    await query.answer()
    try:
        callback_data = query.data
        _, ray_id = callback_data.split(":")
        sql_str = sql_service.get_sql_strs_by_ray_id(ray_id).value
        await  context.bot.send_message(chat_id, text=sql_str)
    except Exception as e:
        traceback.print_exc()