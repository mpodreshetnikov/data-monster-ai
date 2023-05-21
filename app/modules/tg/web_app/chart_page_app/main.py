import os

DIR_DIR = os.path.realpath(os.path.dirname(__file__))

def build_chart_page(question:str, js_code_insertion: str) -> str:
    with open(os.path.join(DIR_DIR, 'source', 'index.html'), 'r', encoding='UTF-8') as file:
        data = file\
            .read()\
            .replace('<!--[JS_CODE_INSERTION]-->', js_code_insertion)\
            .replace('<!--[QUESTION_INSERTION]-->', question)
    return data
