from pydantic import Field

from langchain.agents.agent_toolkits.base import BaseToolkit
from langchain.base_language import BaseLanguageModel
from langchain.tools import BaseTool
from langchain.embeddings.base import Embeddings
from langchain.tools.vectorstore.tool import VectorStoreQATool
from langchain.tools.human import HumanInputRun

from db_data_interaction.db_hints_tool import get_db_hints_tools
from db_data_interaction.db_description_tool import SQLDatabaseToolkitModified, InfoSQLDatabaseWithCommentsTool
from db_data_interaction.query_hints_tool import SQLQueryHintsToolkit, SQLQueryHint


class DbDataInteractionToolkit(SQLDatabaseToolkitModified, BaseToolkit):
    db_hints_doc_path: str = Field(description="Path to the database documentation")
    sql_query_examples_path: str = Field(description="Path to the YAML file with the query examples")
    llm: BaseLanguageModel = Field()
    embeddings: Embeddings = Field()

    sql_query_hints_toolkit: SQLQueryHintsToolkit = None
    tools: list[BaseTool] = []

    def build(self):
        tools: list[BaseTool] = []
        tools.extend(SQLDatabaseToolkitModified.get_tools(self))
        tools.extend([HumanInputRun()])
        if self.db_hints_doc_path:
            db_doc_tools = get_db_hints_tools(self.llm, self.db_hints_doc_path)
            tools.extend(db_doc_tools)
        if self.sql_query_examples_path:
            self.sql_query_hints_toolkit = SQLQueryHintsToolkit(
                queries_path=self.sql_query_examples_path, embed_model=self.embeddings)
            self.sql_query_hints_toolkit.build()
            tools.extend(self.sql_query_hints_toolkit.get_tools())
        self.tools = tools

    def get_tools(self) -> list[BaseTool]:
        return self.tools
    
    def get_db_hint(self, query: str) -> str:
        if not self.db_hints_doc_path:
            return "no hint available"
        tool: VectorStoreQATool = next(filter(lambda t: isinstance(t, VectorStoreQATool), self.tools), None)
        if not tool:
            return "no hint available"
        return tool.run(query)
    
    def get_query_hints(self, query: str, limit: int) -> list[SQLQueryHint]:
        if not self.sql_query_hints_toolkit:
            return "no hints available"
        return self.sql_query_hints_toolkit.get_top_hints(query, limit)
    
    def get_table_info(self, table: str) -> str:
        tool: InfoSQLDatabaseWithCommentsTool = next(filter(lambda t: isinstance(t, InfoSQLDatabaseWithCommentsTool), self.tools), None)
        if not tool:
            return "no info available"
        return tool.run(table)