from langchain.tools import tool

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy import inspect
from sqlalchemy.sql import text
from sqlalchemy.engine import URL


@tool
def get_comments(url: str) -> str:
    """Retrieves all comments for tables and columns from database."""
    engine = create_engine(url)
    meta = MetaData()
    MetaData.reflect(meta, bind = engine)

    with engine.connect() as con:

        statement_cols = text("""select
    c.table_name,
    c.column_name,
    pgd.description
from pg_catalog.pg_statio_all_tables as st
inner join pg_catalog.pg_description pgd on (
    pgd.objoid = st.relid
)
inner join information_schema.columns c on (
    pgd.objsubid   = c.ordinal_position and
    c.table_schema = st.schemaname and
    c.table_name   = st.relname
);""")
    statement_tables = text("""SELECT obj_description(oid), relname
FROM pg_class
WHERE relkind = 'r'
""")
    response_cols = con.execute(statement_cols)
    response_tables = con.execute(statement_tables)
    results_cols = response_cols.mappings().all()
    results_tables = response_tables.mappings().all()
    fin_tables = [d for d in results_tables if all(d.values())]
    fin_cols = [d for d in results_tables if all(d.values())]

    return str([fin_tables, fin_cols])

test_url = URL.create(
    "postgresql",
    username="gpt_bi_user",
    password="uzH#Q%N9YvM3f!",  
    host="62.109.28.9",
    port="2401",
    database="dwh_uas",
)

get_comments(test_url)