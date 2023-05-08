import re
from typing import Optional
from pydantic import Field

from sqlalchemy.schema import CreateTable

from langchain import SQLDatabase
from langchain.agents.agent_toolkits.base import BaseToolkit
from langchain.base_language import BaseLanguageModel
from langchain.callbacks.manager import (
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



class InfoSQLDatabaseWithCommentsTool(InfoSQLDatabaseTool):

    description = """
    Input to this tool is a comma-separated list of tables, output is the schema: columns, foreign keys and sample rows for those tables.
    Be sure that the tables actually exist by calling 'list_tables_sql_db' first and don't ask more than one tables once!

    Example Input: "table1"
    """


    def _run(
        self,
        table_name: str,
        tool_input: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        # table_names = table_names.split(", ")
        table_names = [table_name]
        ### Method was taken from InfoSQLDatabaseTool and modified to include column comments ###

        try:
            all_table_names = self.db.get_usable_table_names()
            if table_names is not None:
                missing_tables = set(table_names).difference(all_table_names)
                if missing_tables:
                    raise ValueError(f"table_names {missing_tables} not found in database")
                all_table_names = table_names

            meta_tables = [
                tbl
                for tbl in self.db._metadata.sorted_tables
                if tbl.name in set(all_table_names)
                and not (self.db.dialect == "sqlite" and tbl.name.startswith("sqlite_"))
            ]

            tables = []
            for table in meta_tables:
                if self.db._custom_table_info and table.name in self.db._custom_table_info:
                    tables.append(self.db._custom_table_info[table.name])
                    continue

                create_table = str(CreateTable(table).compile(self.db._engine))
                table_info = f"{create_table.rstrip()}"
                has_extra_info = (
                    self.db._indexes_in_table_info or self.db._sample_rows_in_table_info
                )

                # add column comments
                for column in table.columns:
                    if column.comment:
                        f_pattern = r"(" + column.name + r"[^,\n]*)(,?\n?)"
                        s_pattern = r"\1 COMMENT '" + column.comment + r"'\2"
                        table_info = re.sub(f_pattern, s_pattern, table_info, count=1)

                if has_extra_info:
                    table_info += "\n\n/*"
                if self.db._indexes_in_table_info:
                    table_info += f"\n{self.db._get_table_indexes(table)}\n"
                if self.db._sample_rows_in_table_info:
                    table_info += f"\n{self.db._get_sample_rows(table)}\n"
                if has_extra_info:
                    table_info += "*/"
                tables.append(table_info)
            final_str = "\n\n".join(tables)
            return final_str
        except ValueError as e:
            """Format the error message"""
            return f"Error: {e}"
 

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
            InfoSQLDatabaseWithCommentsTool(db=self.db),
            ListSQLDatabaseWithCommentsTool(db=self.db),
            QueryCheckerTool(db=self.db, llm=self.llm),
        ]