import json
from typing import Optional


from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
)
from langchain.chains import RetrievalQA
from langchain.tools.base import BaseTool
from langchain.tools.vectorstore.tool import VectorStoreQATool

class VectorStoreQATool(VectorStoreQATool, BaseTool):
    """Tool for the VectorDBQA chain. To be initialized with name and chain."""

    @staticmethod
    def get_description(name: str, description: str) -> str:
        template: str = (
            "Useful for when you need to answer questions about {name}. "
            "Whenever you need information about {description} "
            "you should ALWAYS use this. "
            "Input should be a fully formed question."
        )
        return template.format(name=name, description=description)

    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool asynchronously."""
        chain = RetrievalQA.from_chain_type(
            self.llm, retriever=self.vectorstore.as_retriever()
        )
        await chain.arun(query)
