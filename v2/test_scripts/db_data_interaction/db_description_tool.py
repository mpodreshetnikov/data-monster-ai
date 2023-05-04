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



class InfoSQLDatabasewithCommentsTool(InfoSQLDatabaseTool):

    def _run(
        self,
        table_name: str,
        tool_input: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        column_strings = []
        
        table = self.db._metadata.tables[table_name]
        for column in table.columns:
            comment = column.comment
            if comment:
                column_strings.append(f"{column.name} ({comment})")
            else:
                column_strings.append(column.name)

        
        return ", ".join(column_strings)

 

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
            InfoSQLDatabasewithCommentsTool(db=self.db),
            ListSQLDatabaseWithCommentsTool(db=self.db),
            QueryCheckerTool(db=self.db, llm=self.llm),
        ]
