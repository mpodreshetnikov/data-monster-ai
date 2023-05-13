from langchain.prompts import PromptTemplate

template = """You are a translator from English to Russian.
Translate this text:
{text_to_translate}
The final version of the translation:"""


translator_prompt= PromptTemplate(input_variables=["text_to_translate"], template=template)