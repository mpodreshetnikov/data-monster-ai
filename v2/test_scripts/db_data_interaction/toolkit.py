from pydantic import Field

# from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.agents.agent_toolkits.base import BaseToolkit
from langchain.tools import BaseTool
from langchain.tools.human import HumanInputRun

from db_data_interaction.db_hints_tool import get_db_hints_toolkit
from db_data_interaction.db_description_tool import SQLDatabaseToolkitModified
from db_data_interaction.query_hint_tool import get_query_hint_toolkit

class DbDataInteractionToolkit(SQLDatabaseToolkitModified, BaseToolkit):
    db_doc_path: str = Field(description="Path to the database documentation")
    json_path: str = Field(description="he path to the JSON file with the query examples")
    def get_tools(self) -> list[BaseTool]:
        tools: list[BaseTool] = []
        tools.extend(SQLDatabaseToolkitModified.get_tools(self))
        tools.extend([HumanInputRun()])
        if self.db_doc_path:
            db_doc_tool = get_db_hints_toolkit(self.db_doc_path)
            tools.extend(db_doc_tool.get_tools())
        if self.json_path:
            query_examples_tool = get_query_hint_toolkit(self.json_path)
            tools.extend(query_examples_tool.get_tools())
        return tools