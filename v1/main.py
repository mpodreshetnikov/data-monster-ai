import configparser, logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import tg_bot.tg_main as tg_main
from tg_bot.correction import add_correction_handler
import json_fixer

json_fixer.fix_serialiazing()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s | %(message)s",
    level=logging.INFO,
    filename="log.txt",
    force=True,
)
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    # configure
    config = configparser.ConfigParser()
    config.read("settings.ini")
    
    application = ApplicationBuilder().token(config["telegram"]["Token"]).concurrent_updates(True).build()

    application.add_handler(CommandHandler('start', tg_main.start))

    # handlers, required order
    add_correction_handler(application)
    application.add_handler(CommandHandler('debug', lambda update, context: tg_main.answer_question(update, context, debug=True)))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tg_main.answer_question))

    application.add_error_handler(lambda _, context: logger.error(context.error, exc_info=True))

    logger.info("Start application")
    application.run_polling()



# Делать умные ретраи - увеличивать колво ответов до 3 или менять температуру
# Пробовать подбирать температуру с помощью ИИ
# генерация текстовых подсказок в виде плана ответа
# transcribe question from audio
# скачивание эксель файла с таблицей при необходимости
# data request suggestions
# challenge: save correctness of corrections due database tables refactoring
# challenge: data aggregation from different sources (2 DBs for example)

# как улучшал качество
# было 5% шанс корректного запроса
# 1) поставил температуру 0.05 и запрос 3-х ответов сразу с попыткой запустить в бд хотя бы один
# стало: 10% шанс корректного запроса, но в бесплатной версии часто вылетает ошибка о загруженности модели
# 2) улучшил качество нейминга таблиц (соотв смыслу и грамотность)
# 3) почистил слабые нейминги колонок таблиц по схожести между внешними ключами similarity(column_name, confrelid::regclass::text) FROM pg_constraint
# стало: без изменений
# 4) поставил температуру 0.1, тк иногда все 3 запроса одинаковые
# стало: хуже, запросы стали слишком выдуманными без соответствия схеме, вернул на 0.05
# 5) добавил возможность корректировать ответы бота и тем самым дообучать (через примеры в prompt)
# сильно возросло качество ответов бота при внесении хотя бы одной корректировке на схожие связи таблиц (% сложно подсчитать ~80%)
# 6) перешел на модель gpt-3.5-turbo тк она быстрее и дешевле
# 7) изменил промпт для формировани информации о таблицах в бд на тот который модель лучше понимает + с внешними ключами
# 8) изменил шаблон промпта, добавил больше инструкций и правил -> модель стала допускать меньше ошибок
# 9) добавил индекс для поиска из всех таблиц наилучших по запросу пользователя, чтобы передавать меньше данных в модель и экономить промты
# 10) добавил контекст диалога с небольшой глубиной (с вопросом и данными из ответа, именно данными из базы), чтобы модель могла использовать их в следующих ответах (например, конкретные названия или идентификаторы, которые подразумевает юзер)
#