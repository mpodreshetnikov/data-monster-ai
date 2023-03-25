import configparser
from my_types import Interaction, AnswerType
import answering.prompts as prompts, ai
from dbaccess import DbAccess
from tg_bot.correction import CorrectionDbAccess
import logging, json
from pandas import DataFrame
from matplotlib.figure import Figure
import answering.drawer as drawer

# configure
config = configparser.ConfigParser()
config.read("settings.ini")

DrawingTestMode: bool = config.getboolean("drawing", "TestMode")
CorrectionsLimit: int = int(config["corrections"]["Limit"])

logger = logging.getLogger(__name__)

def answer(interaction: Interaction) -> Interaction:
    global CorrectionsLimit

    dbaccess = DbAccess("db")
    db_schema = dbaccess.get_db_schema_via_sql()

    corr_dbaccess = CorrectionDbAccess("corrections_db")
    examples = corr_dbaccess.get_good_corrections(interaction.question, CorrectionsLimit)
    logger.info(f"Got {len(examples)} examples for prompt")

    prompt = prompts.prepare_sql_prompt(db_schema, interaction.question, examples)
    logger.info(f"Prompt builded")

    logger.info(f"Generation AI answers")
    ai_db_requests = list(map(prompts.restore_sql_prompt, ai.generate_answer_code(prompt, prompts.prepare_sql_stop_sequences())))
    logger.info(f"{len(ai_db_requests)} AI answers generated")

    dbaccess.try_set_answer_with_db_requests(interaction, ai_db_requests)
    logger.info(f"Answer generated")
    logger.info(json.dumps(interaction))
    if interaction.answer_type == None:
        try_set_type_of_answer(interaction)
        logger.info(f"Answer type changed to {interaction.answer_type}")
    
    return interaction


def try_set_type_of_answer(interaction: Interaction) -> None:
    plot_pointing_substrings = ["plot", "graphic", "chart", "figure", "график", "диаграмм", "зависимост"]
    
    if DrawingTestMode:
        interaction.answer_type = AnswerType.PLOT
    elif interaction.answer_result.size == 1:
        interaction.answer_type = AnswerType.NUMBER
    elif any(substring in interaction.question for substring in plot_pointing_substrings):
        interaction.answer_type = AnswerType.PLOT
    else:
        interaction.answer_type = AnswerType.TABLE


def create_and_set_figure(interaction: Interaction) -> Interaction:
    prompt = prompts.prepare_figure_prompt(interaction)
    logger.info(f"Prompt builded for figure\n{prompt}")

    ai_db_requests = list(map(prompts.restore_figure_prompt, ai.generate_answer_code(prompt, prompts.prepare_figure_stop_sequences())))

    if DrawingTestMode:
        ai_db_requests = ["""def draw_figure(data: DataFrame) -> Figure:
    fig, ax = plt.subplots()
    ax.plot(data['week'], data['total_amount'])
    ax.set(xlabel='week', ylabel='total_amount',
           title='Salary Payments')
    ax.grid()
    fig.autofmt_xdate()
    return fig"""]
        interaction.answer_result = DataFrame({'week': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 'total_amount': [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]})

    for ai_db_request in ai_db_requests:
        try:
            figure = drawer.create_figure(interaction.answer_result, ai_db_request)
            interaction.set_figure(figure, ai_db_request)
            return interaction
        except Exception as e:
            logger.error(e, exc_info=True)
            continue