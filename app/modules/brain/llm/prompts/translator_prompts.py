from langchain import PromptTemplate, FewShotPromptTemplate


examples = [
    {
        "text": "Вася Пупкин продал больше всех машин - 8 штук",
        "tr_text": "Вася Пупкин продал больше всех машин - 8 штук",
    },
    {"text": "The answer seems to be empty", "tr_text": "Ответ кажется пустым"},
]

example_formatter_template = """Text to be translated: {text}
Text in Russian language: {tr_text}
"""

TRANSLATOR_PREFIX = """You are a translator only from English to Russian and from Russian to Russian.
Below are examples:"""

TRANSLATOR_SUFFIX = """
Text to be translated: {input}
Text in Russian language:
"""

example_prompt = PromptTemplate(
    input_variables=["text", "tr_text"],
    template=example_formatter_template,
)

TRANSLATOR_PROMPT = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    prefix=TRANSLATOR_PREFIX,
    suffix=TRANSLATOR_SUFFIX,
    input_variables=["input"],
    example_separator="\n",
)