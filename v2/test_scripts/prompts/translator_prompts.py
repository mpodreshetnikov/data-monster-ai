from langchain.prompts import PromptTemplate

__TRANSLATOR_TEMPLATE__ = """You are a translator from English to Russian.
Translate this text:
{text_to_translate}
The final version of the translation:"""
TRANSLATOR_PROMPT = PromptTemplate.from_template(__TRANSLATOR_TEMPLATE__)