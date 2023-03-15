from tg_bot.correction import Correction


def prepare_db_schema(db_schema_by_table_strings):
    # remove extra spaces and write as comments (with #)
    cleaned_schema = list(map(lambda x: "# " + " ".join(x.split()).replace("\n", ""), db_schema_by_table_strings))
    return '\n'.join(cleaned_schema)


def prepare_db_promt_part(db_schema: list[str]):
    summarized_db_info = prepare_db_schema(db_schema)
    # create part of prompt with db
    return "### Postgres SQL tables, with their properties:\n#\n" + summarized_db_info


def prepare_examples(examples: list[Correction]) -> str:
    new_line = "\n"
    joining = "\n# "

    examples_strs = "\n".join(map(lambda x: f"""#
# Example
# Question: {x.question}
# {joining.join(x.answer.split(new_line))}""" , examples))
    
    return f"\n#\n### Examples\n{examples_strs}"


def prepare_prompt(db_schema: list[str], question: str, examples: list[Correction] = []) -> str:
    db_part_prompt = prepare_db_promt_part(db_schema)

    # create part of prompt with request
    request_part_prompt = f"\n#\n### Question: {question} \nSELECT"

    examples_str = ""
    if len(examples):
        examples_str = prepare_examples(examples)

    # create full prompt text
    return db_part_prompt + examples_str + request_part_prompt