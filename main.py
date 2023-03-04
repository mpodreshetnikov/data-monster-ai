import dbaccess, ai, answering, drawer
import psycopg, configparser, os, openai.error
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE, debug=False):
    chat_id = update.effective_chat.id

    await context.bot.send_message(chat_id, text="Собираю данные...")
    question = " ".join(context.args) if context.args else update.message.text
    try:
        answer = answering.answer(question)
    except openai.error.RateLimitError as e:
        await context.bot.send_message(chat_id, text=f"Превышен лимит запросов, попробуйте позже")
        if debug: await context.bot.send_message(chat_id, text=e.user_message)
        return
    except Exception as e:
        await context.bot.send_message(chat_id, text="Неизвестная ошибка, попробуйте еще раз")
        if debug: await context.bot.send_message(chat_id, text=str(e))
        return

    if debug: await context.bot.send_message(chat_id, text=str(answer[1]))
    match answer[2]:
        case answering.AnswerType.ERROR:
            await context.bot.send_message(chat_id, text="Ошибка сбора данных, попробуйте изменить запрос")
            return
        case answering.AnswerType.NUMBER:
            await context.bot.send_message(chat_id, text=str(answer[0].iat[0, 0]))
        case answering.AnswerType.TABLE:
            filename = f"{datetime.now().strftime('%d_%m_%Y_%H_%M_%S')}_{question.replace(' ', '_')}_{update.effective_user.id}.png"
            drawer.draw_table(answer[0], filename)
            try:
                await context.bot.send_photo(chat_id, photo=filename)
            finally:
                os.remove(filename)
    
    await context.bot.send_message(chat_id, text="Что еще хочешь узнать?")
    

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Что хочешь узнать?")

if __name__ == '__main__':
    # configure
    config = configparser.ConfigParser()
    config.read("settings.ini")

    ai.set_openai_api_key(config["openai"]["ApiKey"])
    dbaccess.db_conn = psycopg.connect(
        host = config["db"]["Host"],
        dbname = config["db"]["Database"],
        user = config["db"]["User"],
        password = config["db"]["Password"],
        port = config["db"]["Port"]
    )
    
    application = ApplicationBuilder().token(config["telegram"]["Token"]).concurrent_updates(True).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('debug', lambda update, context: answer(update, context, debug=True)))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))

    application.run_polling()



# добавить внешние ключи
# graphic requests
# скачивание эксель файла при необходимости
