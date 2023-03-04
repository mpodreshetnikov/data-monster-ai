def prepare_db_schema(db_schema_by_table_strings):
    # remove extra spaces and write as comments (with #)
    cleaned_schema = list(map(lambda x: "# " + " ".join(x.split()).replace("\n", ""), db_schema_by_table_strings))
    return '\n'.join(cleaned_schema)

def prepare_db_promt_part(db_schema_by_table_strings):
    summarized_db_info = prepare_db_schema(db_schema_by_table_strings)
    # create part of prompt with db
    return "### Postgres SQL tables, with their properties:\n#\n" + summarized_db_info

def prepare_prompt(db_schema_by_table_strings, question):
    db_part_prompt = prepare_db_promt_part(db_schema_by_table_strings)
    # create part of prompt with request
    request_part_prompt = f"\n#\n### Запрос на {question} \nSELECT"
    # create full prompt text
    return db_part_prompt + request_part_prompt