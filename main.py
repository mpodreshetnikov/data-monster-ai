import re, openai, psycopg2, configparser

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

def prepare_db_schema(db_schema_by_table_strings):
    # remove extra spaces and write as comments (with #)
    cleaned_schema = list(map(lambda x: "# " + " ".join(x.split()).replace("\n", ""), db_schema_by_table_strings))
    return '\n'.join(cleaned_schema)

def prepare_db_promt_part():
    db_schema = get_db_schema_via_sql()
    summarized_db_info = prepare_db_schema(db_schema)
    # create part of prompt with db
    return "### Postgres SQL tables, with their properties:\n#\n" + summarized_db_info

def prepare_prompt(question):
    db_part_prompt = prepare_db_promt_part()
    # create part of prompt with request
    request_part_prompt = f"\n#\n### Запрос на {question} \nSELECT"
    # create full prompt text
    return db_part_prompt + request_part_prompt

def get_ai_response(prompt):
    response = openai.Completion.create(
        model="code-davinci-002",
        prompt=prompt,
        temperature=0,
        max_tokens=150,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=["#", ";"]
    )
    return response.choices[0].text

def prepare_ai_db_request(prompt):
    ai_response = get_ai_response(prompt)
    return f"SELECT {ai_response}"

def do_db_request(sql):
    with db_conn.cursor() as cur:
        try:
            cur.execute(sql)
            result = cur.fetchall() if cur.rowcount else "NO DATA"
            columns = list(map(lambda x: x.name, cur.description))
            return (columns, result)
        except Exception as e:
            return "ERROR"

def answer_to_question(question):
    prompt = prepare_prompt(question)
    ai_db_request = prepare_ai_db_request(prompt)
    db_response = do_db_request(ai_db_request)
    return (ai_db_request, db_response)




# configure
config = configparser.ConfigParser()
config.read("settings.ini")

# setup
openai.api_key = config["openai"]["ApiKey"]
db_conn = psycopg2.connect(
    host = config["db"]["Host"],
    dbname = config["db"]["Database"],
    user = config["db"]["User"],
    password = config["db"]["Password"],
    port = config["db"]["Port"]
)

# answering
question = "названия архивных приемов пищи гис"
answer = answer_to_question(question)
print(answer)


db_conn.close()





# do no_data message when cur.rowcount = 0

# учесть причины остановки генерации ответа
# simple requests
# graphic requests
# table requests
