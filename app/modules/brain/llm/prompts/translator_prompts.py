from langchain import PromptTemplate, FewShotPromptTemplate


examples = [
    {
        "text": "Коровина Наталья Васильевна продала больше всех анальгина - 8 штук",
        "tr_text": "Коровина Наталья Васильевна продала больше всех анальгина - 8 штук",
    },
    {"text": "The answer seems to be empty", "tr_text": "Ответ кажется пустым"},
]

example_formatter_template = """Text to be translated: {text}
Translated text: {tr_text}
"""

TRANSLATOR_PREFIX = """You are a translator from English into Russian. If the text came in Russian, then you leave it in Russian"""

TRANSLATOR_SUFFIX = """
Text to be translated: {input}
Translated text:
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
