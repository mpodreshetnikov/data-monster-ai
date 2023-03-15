from my_types import Answer, AnswerType
import pandas as pd, psycopg
import configparser

class NoValidSqlException(Exception):
    def __init__(self, message: str, sqls: list[str]):            
        super().__init__(message)
        self.sqls = sqls

class DbAccess():
    def __init__(self, db_config_section_name: str) -> None:
        config = configparser.ConfigParser()
        config.read("settings.ini")
        db_config_section = config[db_config_section_name]
        self.db_conn: psycopg.Connection = psycopg.connect(
            host = db_config_section["Host"],
            dbname = db_config_section["Database"],
            user = db_config_section["User"],
            password = db_config_section["Password"],
            port = db_config_section["Port"]
        )
        self.UseWeakForeignKeys: bool = config.getboolean("db_schema", "UseWeakForeignKeys")
        self.WeakForeignKeysThreshold: float = float(config["db_schema"]["WeakForeignKeysThreshold"])


    def get_db_schema_via_sql(self) -> list[str]:
        schema = []
        with self.db_conn.cursor() as cur:
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
                cur.execute("""
    SELECT column_name, data_type, is_nullable, col_description(concat('"', table_name, '"')::regClass, ordinal_position)
    FROM information_schema.columns
    WHERE table_name = %(table)s
    ORDER BY ordinal_position;
    """, { 'table': table[0] })
                response = cur.fetchall()
                # convert columns to strings in style if desc exists '(колонка)column: uuid NOT NULL'
                columns_strings = list(map(lambda x: f"{f'({x[3]})' if x[3] else ''}{x[0]}: {x[1]}{' NOT NULL' if x[2] == 'NO' else ''}", response))

                # write to schema string
                schema.append(f"TABLE[{table[1]}] COLUMNS[{', '.join(columns_strings)}]")

            # add information about mapping foreign columns with hard names to understand
            if self.UseWeakForeignKeys:
                cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                cur.execute("""
    SELECT DISTINCT column_name, confrelid::regclass::text
    FROM pg_constraint
    JOIN information_schema.columns ON table_name = conrelid::regclass::text
    WHERE contype = 'f'
        AND connamespace = 'public'::regnamespace
        AND ordinal_position = any(conkey)
        AND similarity(column_name, confrelid::regclass::text) <= %(threshold)s
    ;
    """, { 'threshold': self.WeakForeignKeysThreshold })
                response = cur.fetchall()
                mapping_strings = list(map(lambda x: f"{x[0]} -> {x[1]}", response))
                schema.append("")
                schema.append("### Use following foreign key mappings [column -> foreign table]:")
                for maping_string in mapping_strings: schema.append(maping_string)
                
        return schema


    def try_db_requests(self, sql_requests: list[str]) -> Answer:
        for sql in sql_requests:
            with self.db_conn.cursor() as cur:
                try:
                    cur.execute(sql)
                    if not cur.rowcount:
                        return Answer(None, answer_code=sql, type=AnswerType.NO_DATA)
                    data = cur.fetchall()
                    columns = list(map(lambda x: x.name, cur.description))
                    return Answer(pd.DataFrame(data, columns=columns), answer_code=sql)
                except Exception:
                    self.db_conn.rollback()
        raise NoValidSqlException("No valid SQLs", sql_requests)