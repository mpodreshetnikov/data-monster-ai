from langchain import PromptTemplate, FewShotPromptTemplate


_examples = [
    {
        "text": "Коровина Наталья Васильевна продала больше всех анальгина - 8 штук",
        "tr_text": "Коровина Наталья Васильевна продала больше всех анальгина - 8 штук",
    },
    {
        "text": "The answer seems to be empty",
        "tr_text": "Ответ кажется пустым"
    },
]

_EXAMPLE_FORMATTER_TEMPLATE = """
Text to be translated: {text}
Text in Russian: {tr_text}"""

_TRANSLATOR_PREFIX = """You are a translator only from English to Russian."""

_TRANSLATOR_SUFFIX = """
Text to be translated: {input}
Text in Russian: """

_example_prompt = PromptTemplate(
    input_variables=["text", "tr_text"],
    template=_EXAMPLE_FORMATTER_TEMPLATE,
)

TRANSLATOR_PROMPT = FewShotPromptTemplate(
    examples=_examples,
    example_prompt=_example_prompt,
    prefix=_TRANSLATOR_PREFIX,
    suffix=_TRANSLATOR_SUFFIX,
    input_variables=["input"],
    example_separator="\n",
)

print(TRANSLATOR_PROMPT.format(input="The answer seems to be empty"))
