from langchain.prompts import PromptTemplate

TRANSLATOR_TEMPLATE = """You are a translator from English to Russian.
Translate this text:
{text_to_translate}
The final version of the translation:"""


TRANSLATOR_PROMPT= PromptTemplate(input_variables=["text_to_translate"], template=TRANSLATOR_TEMPLATE)