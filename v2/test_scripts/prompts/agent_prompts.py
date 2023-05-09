SQL_PREFIX = """You are an agent designed to interact with a SQL database to respond to a user request.
Given an input question, create syntactically correct {dialect} queries to run.

Unless the user specifies a specific number of examples they want, always limit your query to no more than {top_k} results (LIMIT {top_k}).
Never query all columns from a particular table, query only the relevant columns given the question.
Never consider removed and archived entities unless you are asked to.
Never use ''' '''.
DO NOT query non-existent columns. Check table information before querying the database!
DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP, etc.) on the database.

If the question does not seem related to the information from the database or you messed up, try the following:
1) look for hints via database hints tool.
"""


SQL_SUFFIX = """Begin!

Question: {input}
Thought: {agent_scratchpad}"""


from db_data_interaction.toolkit import DbDataInteractionToolkit

from utils.color import BOLD, END

import datetime

def get_formatted_prefix_with_additional_info(
        toolkit: DbDataInteractionToolkit, question: str, query_hints_limit: int = 1, prefix: str = SQL_PREFIX
):
    # Получаем подсказку для базы данных
    db_hint = toolkit.get_db_hint(question)

    # Получаем подсказки для запроса
    query_hints_list = toolkit.get_query_hints(question, query_hints_limit)

    # Формируем строку с подсказками для вывода
    query_hints = '\n'.join(
                    [f"{BOLD}Question:{END} {hint.question}\n{BOLD}Query:{END}\n{hint.query}" for hint in query_hints_list]
                    ) if len(query_hints_list) > 0 else None

    # Получаем уникальные таблицы из подсказок и получаем информацию о каждой таблице
    unique_tables = list(set(table for hint in query_hints_list for table in hint.tables))
    tables_info = '\n'.join(toolkit.get_table_info(table) for table in unique_tables)

    # Формируем строку с информацией о таблицах и примерами похожих запросов для вывода
    db_hint_str =  f'{BOLD}Some hints:{END} {db_hint}' if db_hint else None
    table_info_str = ('\nAlso we have prepared A FEW tables from the database '
                    f'that may be usefull to answer the user\'s question: {BOLD}{unique_tables}{END}.'
                    '\nIf the tables are not enough to answer the user\'s question you have to lookup all the available tables in the database.'
                    f'\n{tables_info}'
                    ) if len(unique_tables) > 0 else None
    query_hints_str = (f'\n\nAlso a few examples of sql-queries similar to user\'s question:\n\n{query_hints}'
                    ) if query_hints else None

    # Объединяем информацию о таблицах и примеры запросов в SQL_PREFIX
    result_str = [i for i in [prefix, db_hint_str, table_info_str, query_hints_str] if i is not None]
    
    # Добавляем информацию о времени
    date_today = datetime.date.today()
    result_str.insert(0, f"Todays date is {date_today}")
    
    return '\n'.join(result_str)