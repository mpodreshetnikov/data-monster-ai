SQL_PREFIX = """You are an agent designed to interact with a SQL database to respond to a user request.
Given an input question, create syntactically correct {dialect} queries to run.

Unless the user specifies a specific number of examples they want, always limit your query to no more than {top_k} results.
Never query all columns from a particular table, query only the relevant columns given the question.
Never consider remote entities unless you are asked to.
DO NOT query non-existent columns. Check table information before querying the database!
DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP, etc.) on the database.
"""


SQL_SUFFIX = """Begin!

Question: {input}
Thought: {agent_scratchpad}"""


from db_data_interaction.toolkit import DbDataInteractionToolkit

from utils.color import BOLD, END


def get_formatted_prefix_with_additional_info(
        toolkit: DbDataInteractionToolkit, question: str, query_hints_limit: int = 1, prefix: str = SQL_PREFIX
):
    # Получаем подсказку для базы данных
    db_hint = toolkit.get_db_hint(question)

    # Получаем подсказки для запроса
    query_hints = toolkit.get_query_hints(question, query_hints_limit)

    # Формируем строку с подсказками для вывода
    query_hints_str = '\n'.join([f"{BOLD}Question:{END} {hint.question}\n{BOLD}Query:{END}\n{hint.query}" for hint in query_hints])

    # Получаем уникальные таблицы из подсказок и получаем информацию о каждой таблице
    unique_tables = list(set(table for hint in query_hints for table in hint.tables))
    tables_info = '\n'.join(toolkit.get_table_info(table) for table in unique_tables)

    # Формируем строку с информацией о таблицах и примерами похожих запросов для вывода
    db_hint_str = f'{BOLD}Some hints:{END} {db_hint}'
    table_info_str = ('\nAlso we have prepared tables from the database '
                    f'that may be usefull to answer the user\'s question: {BOLD}{unique_tables}{END}.'
                    f'\n{tables_info}')    
    query_hints_str = f'\n\nAlso a few examples of sql-queries similar to user\'s question:\n\n{query_hints_str}'

    # Объединяем информацию о таблицах и примеры запросов в SQL_PREFIX
    return f"{prefix}\n\n{db_hint_str}\n{table_info_str}\n{query_hints_str}"