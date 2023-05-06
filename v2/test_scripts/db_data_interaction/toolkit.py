from pydantic import Field

# from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.agents.agent_toolkits.base import BaseToolkit
from langchain.tools import BaseTool
from langchain.tools.human import HumanInputRun

from db_data_interaction.db_hints_tool import get_db_hints_toolkit
from db_data_interaction.db_description_tool import SQLDatabaseToolkitModified

class DbDataInteractionToolkit(SQLDatabaseToolkitModified, BaseToolkit):
    db_doc_path: str = Field(description="Path to the database documentation")

    def get_tools(self) -> list[BaseTool]:
        tools: list[BaseTool] = []
        tools.extend(SQLDatabaseToolkitModified.get_tools(self))
        if self.db_doc_path:
            db_doc_tool = get_db_hints_toolkit(self.db_doc_path)
            tools.extend(db_doc_tool.get_tools())
        # tools.append(HumanInputRun())
        return tools