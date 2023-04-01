from tg_bot.correction import Correction
from my_types import Interaction

TEXT_TO_SQL_TMPL = (
    "Given an input question, create a single syntactically correct {dialect} query to run. "
    "You can order the results by a relevant column to return the most "
    "interesting examples in the database.\n"
    "Never query for all the columns from a specific table, only ask for a the "
    "few relevant columns given the question.\n"
    "Pay attention to use only the column names that you can see in the schema "
    "description. "
    "Be careful to not query for columns that do not exist. "
    "Pay attention to which column is in which table. "
    "Also, qualify column names with the table name when needed.\n\n"
    "Use the following format:\n"
    "Question: Question here\n"
    "SQLQuery: SQL Query to run\n\n"
    "Only use the tables listed below.\n\n"
    "{schema}\n\n"
    "And also pay attention to the examples listed below.\n\n"
    "{examples}\n\n"
    "If input question requires to draw plot, table or etc in that way, "
    "just create SQL query which will help to retrive all the needed data with no errors.\n"
    "So, use no comments. If you cannot create the query send to me the word 'Error' "
    "following by error description. But check it twice before send me an Error.\n\n"
    "Question: {query_str}\n"
    "SQLQuery: "
)
TEXT_TO_SQL_STOP_TOKENS = ["SQLResult:", "SQLQuery:"]

TEXT_TO_SQL_EXAMPLE_TMPL = (
    "Question: {question}\n"
    "SQLQuery: \n"
    "{sql_query}\n"
)
TEXT_TO_SQL_NO_EXAMPLES_PROVIDED = "No examples provided. Use only the schema mentioned above."


def prepare_sql_prompt_v2(dialect: str, db_schema: list[str], question: str, examples: list[Correction] = []) -> str:
    db_schema_str = '\n'.join(map(str.strip, db_schema))
    if len(examples):
        examples_str = '\n'.join(map(
            lambda x: TEXT_TO_SQL_EXAMPLE_TMPL.format(question=x.question, sql_query=x.answer),
            examples))
    else:
        examples_str = TEXT_TO_SQL_NO_EXAMPLES_PROVIDED
    return TEXT_TO_SQL_TMPL.format(
        dialect=dialect,
        schema=db_schema_str,
        examples=examples_str,
        query_str=question
    )

def restore_sql_prompt_v2(ai_answer: str) -> str:
    return f"{ai_answer}"

def prepare_sql_stop_sequences_v2() -> list[str]:
    return TEXT_TO_SQL_STOP_TOKENS

def __prepare_db_schema__(db_schema_by_table_strings):
    # remove extra spaces and write as comments (with #)
    cleaned_schema = list(map(lambda x: "-- " + " ".join(x.split()).replace("\n", ""), db_schema_by_table_strings))
    return '\n'.join(cleaned_schema)


def __prepare_db_promt_part__(db_schema_by_table_strings: list[str]):
    summarized_db_info = __prepare_db_schema__(db_schema_by_table_strings)
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