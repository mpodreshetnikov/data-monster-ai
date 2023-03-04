import dbaccess, prompts, ai

def answer(question):
    db_schema = dbaccess.get_db_schema_via_sql()
    prompt = prompts.prepare_prompt(db_schema, question)
    ai_db_request = ai.generate_db_request(prompt)
    db_response = dbaccess.do_db_request(ai_db_request)
    return (ai_db_request, db_response)