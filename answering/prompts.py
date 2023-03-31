from tg_bot.correction import Correction
from my_types import Interaction
import configparser
from llama_index import download_loader


def __prepare_db_schema__(db_schema_by_table_strings):
    # remove extra spaces and write as comments (with #)
    cleaned_schema = list(map(lambda x: "-- " + " ".join(x.split()).replace("\n", ""), db_schema_by_table_strings))
    return '\n'.join(cleaned_schema)


def __load_llama_db_reader__(db_config_section_name: str) -> any:
    var_name = '__llama_db_reader_cashed__'
    if var_name in globals():
        return globals()[var_name]
    
    DatabaseReader = download_loader('DatabaseReader')

    config = configparser.ConfigParser()
    config.read("settings.ini")
    db_config_section = config[db_config_section_name]
    reader = DatabaseReader(
        scheme = "postgresql",
        host = db_config_section["Host"],
        port = db_config_section["Port"],
        user = db_config_section["User"],
        password = db_config_section["Password"],
        dbname = db_config_section["Database"],
    )

    globals()[var_name] = reader
    return reader


def __filter_db_schema_tables__(
        db_schema_by_table_strings: list[str],
        question: Interaction,
        corrections: list[Correction]) -> list[str]:
    
    # filter tables by question context similarity
    llama_db_reader = __load_llama_db_reader__('db')
    for correction in corrections:
        documents = llama_db_reader.load_data(query=correction.answer)
        print(documents)
        


def __prepare_db_promt_part__(
        db_schema_by_table_strings: list[str],
        question: Interaction,
        corrections: list[Correction]):
    filtered_db_schema_by_table_strings = __filter_db_schema_tables__(db_schema_by_table_strings, question, corrections)
    summarized_db_info = __prepare_db_schema__(filtered_db_schema_by_table_strings)
    # create part of prompt with db
    return "-- ### Postgres SQL tables, with their properties:\n--\n" + summarized_db_info


def comment_text(text: str) -> str:
    return "\n".join(map(lambda x: "-- " + x, text.strip().split("\n")))


def prepare_examples(examples: list[Correction]) -> str:
    examples_strs = "\n".join(map(lambda x:\
f"""--
-- Example
-- Question: {x.question}
{comment_text(x.answer)}""" , examples))
    
    return \
f"""
--
-- ### Examples
{examples_strs}"""


def prepare_sql_prompt(db_schema: list[str], question: str, examples: list[Correction] = []) -> str:
    db_part_prompt = __prepare_db_promt_part__(db_schema, question, examples)

    # create part of prompt with request
    request_part_prompt = \
f"""
--
-- ### Use no comments. Question: {question}
SELECT"""

    examples_str = ""
    if len(examples):
        examples_str = prepare_examples(examples)

    # create full prompt text
    return db_part_prompt + examples_str + request_part_prompt


def restore_sql_prompt(ai_answer: str) -> str:
    return f"SELECT {ai_answer}"


def prepare_sql_stop_sequences() -> list[str]:
    return ['#', ';']


def prepare_figure_prompt(interaction: Interaction) -> str:
    return \
f"""### There is following Postgres SQL query:
{comment_text(interaction.answer_code)}
### Your task is to write a single function in Python to draw "{interaction.question}".
### Use matplotlib. Use data from SQL query. Return Figure object. Use no comments.
def draw_figure(data: DataFrame) -> Figure:
"""


def restore_figure_prompt(ai_answer: str) -> str:
    if '```python' in ai_answer:
        code_str = ai_answer.split('```python')[-1].split('```')[0]
        return code_str
    else:
        return f"def draw_figure(data: DataFrame) -> Figure:\n{code_str}"


def prepare_figure_stop_sequences() -> list[str]:
    return ['###', ';', 'def']