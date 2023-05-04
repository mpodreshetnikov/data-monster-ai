from typing import Iterable, Optional
from pydantic import Field

from sqlalchemy.engine import URL

from langchain import SQLDatabase
from langchain.agents.agent_toolkits.base import BaseToolkit
from langchain.base_language import BaseLanguageModel
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools.base import BaseTool
from langchain.tools.sql_database.tool import (
    InfoSQLDatabaseTool,
    ListSQLDatabaseTool,
    QueryCheckerTool,
    QuerySQLDataBaseTool,
)


class ListSQLDatabaseWithCommentsTool(ListSQLDatabaseTool):
    cache_key: str = ""
    cache: str = ""

    def _run(
        self,
        tool_input: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for a specific table."""
        if self.db._include_tables:
            tables_to_take = self.db._include_tables
        else:
            tables_to_take = self.db._all_tables - self.db._ignore_tables

        # return cached data if possible
        cache_key = str.join(",", tables_to_take)
        if cache_key == self.cache_key:
            return self.cache

        table_strings = []
        for table in tables_to_take:
            comment = self.db._inspector.get_table_comment(table, schema=self.db._schema)["text"]
            if comment:
                table_strings.append(f"{table} ({comment})")
            else:
                table_strings.append(table)

        value = ", ".join(table_strings)
        self.cache_key = cache_key
        self.cache = value

        return value



# class InfoSQLDatabaseTool(BaseSQLDatabaseTool, BaseTool):
#     """Tool for getting metadata about a SQL database."""

#     name = "schema_sql_db"
#     description = """
#     Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables.
#     Be sure that the tables actually exist by calling list_tables_sql_db first!

#     Example Input: "table1, table2, table3"
#     """

#     def _run(
#         self,
#         table_names: str,
#         run_manager: Optional[CallbackManagerForToolRun] = None,
#     ) -> str:
#         """Get the schema for tables in a comma-separated list."""
#         return self.db.get_table_info_no_throw(table_names.split(", "))

#     async def _arun(
#         self,
#         table_name: str,
#         run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
#     ) -> str:
#         raise NotImplementedError("SchemaSqlDbTool does not support async")


class SQLDatabaseToolkitModified(BaseToolkit):
    """Toolkit for interacting with SQL databases."""

    db: SQLDatabase = Field(exclude=True)
    llm: BaseLanguageModel = Field(exclude=True)

    @property
    def dialect(self) -> str:
        """Return string representation of dialect to use."""
        return self.db.dialect

    class Config:
        """Configuration for this pydantic object."""

        arbitrary_types_allowed = True

    def get_tools(self) -> list[BaseTool]:
        """Get the tools in the toolkit."""
        return [
            QuerySQLDataBaseTool(db=self.db),
            InfoSQLDatabaseTool(db=self.db),
            ListSQLDatabaseWithCommentsTool(db=self.db),
            QueryCheckerTool(db=self.db, llm=self.llm),
        ]
