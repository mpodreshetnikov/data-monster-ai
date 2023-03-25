from typing import Callable
from my_types import Interaction, AnswerType, ButtonMenuActions
import answering.answering as answering, answering.drawer as drawer, dbaccess, ai
import os, logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Chat started")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Что хочешь узнать?")


async def answer_question(update: Update, context: ContextTypes.DEFAULT_TYPE, debug=False):
    logger.info("answering question started")
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    question = " ".join(context.args) if context.args else update.message.text
    context.user_data["last_question"] = question

    main_button_menu: list[list[InlineKeyboardButton]] = __build_button_menu__([], 1)
    if debug: main_button_menu = __build_button_menu__(
        main_button_menu,
        n_cols=1,
        header_buttons=InlineKeyboardButton("Скорректировать ответ", callback_data=ButtonMenuActions.CORRECT_ANSWER))

    # send pre-message
    await context.bot.send_message(chat_id, text="Собираю данные...")

    logger.info("Building answer..")
    interaction = await __handle_answering_errors__(
        answering.answer,
        Interaction(question),
        context,
        chat_id,
        main_button_menu,
        debug
    )
    if not interaction: return
    logger.info("Answer builded successful")

    # send code in debug mode
    if debug: await context.bot.send_message(chat_id, text=str(interaction.answer_code))

    # send answer by answer type
    match interaction.answer_type:
        case AnswerType.NO_DATA:
            await context.bot.send_message(chat_id, text="Пусто: данные по вашему запросу отсутствуют", reply_markup=InlineKeyboardMarkup(main_button_menu))
        case AnswerType.NUMBER:
            await context.bot.send_message(chat_id, text=str(interaction.answer_result.iat[0, 0]), reply_markup=InlineKeyboardMarkup(main_button_menu))
        case AnswerType.TABLE:
            filename = __build_filename__(question, user_id)
            drawer.save_table_image_to_file(interaction.answer_result, filename)
            try:
                await context.bot.send_photo(chat_id, photo=filename, reply_markup=InlineKeyboardMarkup(main_button_menu))
            finally:
                os.remove(filename)
        case AnswerType.PLOT:
            filename = __build_filename__(question, user_id)
            logger.info("Building figure..")
            interaction = await __handle_answering_errors__(
                answering.create_and_set_figure,
                interaction,
                context,
                chat_id,
                main_button_menu,
                debug
            )
            if not interaction: return
            logger.info("Figure builded successful")

            # send code in debug mode
            if debug: await context.bot.send_message(chat_id, text=str(interaction.figure_code))

            drawer.save_figure_to_file(interaction.figure, filename)
            try:
                await context.bot.send_photo(chat_id, photo=filename, reply_markup=InlineKeyboardMarkup(main_button_menu))
            finally:
                os.remove(filename)
    
    # send post-message
    await context.bot.send_message(chat_id, text="Что еще хочешь узнать?")


async def __handle_answering_errors__(
        answer_call: Callable[[Interaction], Interaction],
        interaction: Interaction,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        main_button_menu: list[list[InlineKeyboardButton]],
        debug: bool = False,
        ) -> Interaction | None:
    user_message = None
    error_message = None
    try:
        interaction = answer_call(interaction)
    except ai.TryAiLaterException as e:
        user_message = "Превышен лимит запросов, попробуйте позже"
        error_message = str(e)
        logger.warning(error_message, exc_info=True)
    except ai.NotCorrectAiAnswerException as e:
        user_message = "Не удается создать качественный запрос к базе, попробуйте изменить запрос"
        error_message = str(e)
    except dbaccess.NoValidSqlException as e:
        user_message = "Ошибка при сборе данных, попробуйте изменить запрос"
        error_message = e.sqls[0]
    except Exception as e:
        user_message = "Неизвестная ошибка, попробуйте еще раз"
        error_message = str(e)
        logger.error(error_message, exc_info=True)

    # if error while building answer -> send err msg and exit
    if error_message:
        logger.warning(f"error due building answer: {error_message}")
        if debug: await context.bot.send_message(chat_id, text=error_message)
        await context.bot.send_message(chat_id, text=user_message, reply_markup=InlineKeyboardMarkup(main_button_menu))
        return None
    return interaction

def __build_filename__(question: str, user_id: int) -> str:
    question_str = question.replace("/", "_").replace(' ', '_').replace('\n', '_')[:40]
    return f"{datetime.now().strftime('%d_%m_%Y_%H_%M_%S')}_{question_str}_{user_id}.png"


def __build_button_menu__(
    buttons: list[InlineKeyboardButton],
    n_cols: int,
    header_buttons: InlineKeyboardButton | list[InlineKeyboardButton] = None,
    footer_buttons: InlineKeyboardButton | list[InlineKeyboardButton] = None
) -> list[list[InlineKeyboardButton]]:
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons if isinstance(header_buttons, list) else [header_buttons])
    if footer_buttons:
        menu.append(footer_buttons if isinstance(footer_buttons, list) else [footer_buttons])
    return menu