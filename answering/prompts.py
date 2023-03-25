from tg_bot.correction import Correction
from my_types import Interaction

def prepare_db_schema(db_schema_by_table_strings):
    # remove extra spaces and write as comments (with #)
    cleaned_schema = list(map(lambda x: "# " + " ".join(x.split()).replace("\n", ""), db_schema_by_table_strings))
    return '\n'.join(cleaned_schema)


def prepare_db_promt_part(db_schema: list[str]):
    summarized_db_info = prepare_db_schema(db_schema)
    # create part of prompt with db
    return "### Postgres SQL tables, with their properties:\n#\n" + summarized_db_info


def comment_text(text: str) -> str:
    return "\n".join(map(lambda x: "# " + x, text.strip().split("\n")))


def prepare_examples(examples: list[Correction]) -> str:
    examples_strs = "\n".join(map(lambda x:\
f"""#
# Example
# Question: {x.question}
{comment_text(x.answer)}""" , examples))
    
    return \
f"""
#
### Examples
{examples_strs}"""


def prepare_sql_prompt(db_schema: list[str], question: str, examples: list[Correction] = []) -> str:
    db_part_prompt = prepare_db_promt_part(db_schema)

    # create part of prompt with request
    request_part_prompt = \
f"""
#
### Use no comments. Question: {question}
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