import yaml
from pydantic import Field

from langchain.agents.agent_toolkits.base import BaseToolkit
from langchain.base_language import BaseLanguageModel
from langchain.tools import BaseTool
from langchain.embeddings.base import Embeddings
from langchain.tools.human import HumanInputRun

from modules.brain.llm.tools.db_data_interaction.db_hints_tool import get_db_hints_tools
from modules.brain.llm.tools.db_data_interaction.db_description_tool import SQLDatabaseToolkitModified, InfoSQLDatabaseWithCommentsTool
from modules.brain.llm.tools.db_data_interaction.query_hints_tool import SQLQueryHintsToolkit, SQLQueryHint

from modules.brain.llm.tools.vectorstore_new.vector_store_qa_tool import VectorStoreQATool

DB_HINT_UNKNOWN_PHRASES = [
    "не знаю", "не могу", "не владею",
    "не имею","невозможно",
    "cannot", "don't know", "can't",
    "don't have", "don't understand", "sorry",
    ]


class DbDataInteractionToolkit(SQLDatabaseToolkitModified):
    db_hints_doc_path: str = Field(default=None, description="Path to the database documentation")
    db_comments_override_path: str = Field(default=None, description="Path to the YAML file with the database comments")
    sql_query_examples_path: str = Field(default=None, description="Path to the YAML file with the query examples")
    llm: BaseLanguageModel = Field()
    embeddings: Embeddings = Field()

    sql_query_hints_toolkit: SQLQueryHintsToolkit = None
    all_tools: list[BaseTool] = []
    available_tools: list[BaseTool] = []

    def build(self):
        self.all_tools = []
        self.available_tools = []

        # add tools available for agent
        if self.db_comments_override_path:
            with open(self.db_comments_override_path, "r", encoding="utf-8") as f:
                db_comments_override = yaml.safe_load(f)["tables"]
        self.available_tools.extend(SQLDatabaseToolkitModified.get_tools(self, db_comments_override=db_comments_override))

        # add all tools available in a script
        self.all_tools.extend(self.available_tools)
        
        self.all_tools.extend([HumanInputRun()])
        if self.db_hints_doc_path:
            db_doc_tools = get_db_hints_tools(self.llm, self.db_hints_doc_path)
            self.all_tools.extend(db_doc_tools)
        if self.sql_query_examples_path:
            self.sql_query_hints_toolkit = SQLQueryHintsToolkit(
                queries_path=self.sql_query_examples_path, embed_model=self.embeddings)
            self.sql_query_hints_toolkit.build()
            self.all_tools.extend(self.sql_query_hints_toolkit.get_tools())

    def get_tools(self) -> list[BaseTool]:
        return self.available_tools
    
    async def get_db_hint(self, query: str) -> str | None:
        if not self.db_hints_doc_path:
            return None
        
        tool: VectorStoreQATool = next(filter(lambda t: isinstance(t, VectorStoreQATool), self.all_tools), None)
        if not tool:
            return None
        
        answer = await tool.arun(query)
        if any((phrase in answer) for phrase in DB_HINT_UNKNOWN_PHRASES):
            return None
        
        return answer
    
    def get_query_hints(self, query: str, limit: int) -> list[SQLQueryHint] | None:
        if not self.sql_query_hints_toolkit:
            return None
        return self.sql_query_hints_toolkit.get_top_hints(query, limit)
    
    def get_table_info(self, table: str) -> str | None:
        tool: InfoSQLDatabaseWithCommentsTool = next(filter(lambda t: isinstance(t, InfoSQLDatabaseWithCommentsTool), self.all_tools), None)
        if not tool:
            return None
        result: str = tool.run(table)
        if "error" in result.lower():
            raise Exception(f"Error while getting table info for {table}: {result}")
        return result