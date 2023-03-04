import re

db_conn = None

def get_db_schema_via_dump():
    # get sql from pgdump
    pgdump = open("pgdump.sql", "r").read()
    # get tables descriptions from pg sql
    return re.findall(r"CREATE TABLE public\.(\w+\s\(\s[^)]+\);)", pgdump)

def get_db_schema_via_sql():
    schema = []
    with db_conn.cursor() as cur:
        # get tables names and descriptions
        cur.execute("""
SELECT table_name, obj_description(concat('"', table_name, '"')::regclass, 'pg_class')
FROM information_schema.tables
WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema');
""")
        response = cur.fetchall()
        # create tuple: table name, table name with desc in style if desc exists '(таблица)table_name'
        tables = list(map(lambda x: (x[0], f"{f'({x[1]})' if x[1] else ''}{x[0]}"), response))
        
        # save tables descriptions as strings
        for table in tables:
            # get columns
            cur.execute(f"""
SELECT column_name, data_type, is_nullable, col_description(concat('"', table_name, '"')::regClass, ordinal_position)
FROM information_schema.columns
WHERE table_name = '{table[0]}'
ORDER BY ordinal_position;
""")
            response = cur.fetchall()
            # convert columns to strings in style if desc exists '(колонка)column: uuid NOT NULL'
            columns_string = list(map(lambda x: f"{f'({x[3]})' if x[3] else ''}{x[0]}: {x[1]} {'NOT NULL' if x[2] == 'NO' else ''}", response))
            # write to schema string
            schema.append(f"{table[1]} [{', '.join(columns_string)}]\n")
    return schema

def do_db_request(sql):
    with db_conn.cursor() as cur:
        try:
            cur.execute(sql)
            result = cur.fetchall() if cur.rowcount else "NO DATA"
            columns = list(map(lambda x: x.name, cur.description))
            return (columns, result)
        except Exception as e:
            return "ERROR"