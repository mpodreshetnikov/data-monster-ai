from typing import List, Optional
import logging

from typing import Any, List, Optional

from langchain import SQLDatabase
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import (
    MetaData,
    text,
    inspect,
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class MultischemaSQLDatabase(SQLDatabase):
    """SQLAlchemy wrapper around a database."""

    def __init__(
        self,
        sync_engine: Engine,
        async_engine: Engine,
        schema: Optional[str] = None,
        metadata: Optional[MetaData] = None,
        ignore_tables: Optional[List[str]] = None,
        include_tables: Optional[List[str]] = None,
        sample_rows_in_table_info: int = 3,
        indexes_in_table_info: bool = False,
        custom_table_info: Optional[dict] = None,
        view_support: bool = False,
    ):
        self._engine = sync_engine
        self._async_engine = async_engine
        self._schema = schema
        self._metadata = metadata or MetaData()
        self.include_tables = include_tables
        self.ignore_tables = include_tables
        self._sample_rows_in_table_info = sample_rows_in_table_info
        self._indexes_in_table_info = indexes_in_table_info
        self._custom_table_info = custom_table_info
        self.view_support = view_support
        self._inspector = inspect(self._engine)

        if include_tables and ignore_tables:
            raise ValueError("Cannot specify both include_tables and ignore_tables")

        self._all_tables = set()
        if self._schema:
            self._all_tables.update(self._inspector.get_table_names(schema=schema))
        else:
            all_schemas = self._inspector.get_schema_names()
            for schema in all_schemas:
                self._all_tables.update(self._inspector.get_table_names(schema=schema))

        self._include_tables = (
            set(self.include_tables) if self.include_tables else set()
        )
        self._ignore_tables = set(self.ignore_tables) if self.ignore_tables else set()
        self._usable_tables = self._get_usable_table_names()
        self._validate_table_names(self._include_tables, self._all_tables)
        self._validate_table_names(self._ignore_tables, self._all_tables)
        self._reflect_tables_in_metadata(self.view_support)

    def _get_usable_table_names(self) -> List[str]:
        if self._include_tables:
            missing_tables = self._include_tables - self._all_tables
            if missing_tables:
                raise ValueError(
                    f"include_tables {missing_tables} not found in database"
                )
            return list(self._include_tables)
        elif self._ignore_tables:
            return list(self._all_tables - self._ignore_tables)
        else:
            return list(self._all_tables)

    def _validate_table_names(self, tables, all_tables):
        if tables:
            if missing_tables := tables - all_tables:
                raise ValueError(f"Tables {missing_tables} not found in database")

    def _reflect_tables_in_metadata(self, view_support: bool):
        """
        Функция выполняет отражение таблиц в метаданных на основе списка usable_tables.

        Args:
            view_support (bool): Флаг, указывающий поддержку представлений.

        Raises:
            ValueError: Если найдено более одной схемы для таблицы или если схема не найдена.

        """
        if self._schema:
            for table_name in self._usable_tables:
                self._metadata.reflect(
                    views=view_support,
                    bind=self._engine,
                    only=[table_name],
                    schema=self._schema,
                )
        else:
            with self._engine.connect() as connection:
                for table_name in self._usable_tables:
                    query = text(
                        "SELECT table_schema FROM information_schema.tables WHERE table_name = :table"
                    )
                    query = query.bindparams(table=table_name)
                    result = connection.execute(query)
                    schemas = [row[0] for row in result.fetchall()]

                    if len(schemas) > 1:
                        logger.error(
                            f"More than one schema found for table {table_name}",
                            exc_info=True,
                        )
                        raise ValueError(
                            f"Найдено более одной схемы для таблицы {table_name}"
                        )

                    if schemas:
                        self._metadata.reflect(
                            views=view_support,
                            bind=self._engine,
                            only=[table_name],
                            schema=schemas[0],
                        )
                    else:
                        logger.error(
                            f"Schema not found for table {table_name}", exc_info=True
                        )
                        raise ValueError(f"Схема не найдена для таблицы {table_name}")

    async def arun(self, command: str, fetch: str = "all") -> str:
        """Execute a SQL command and return a string representing the results.

        If the statement returns rows, a string of the results is returned.
        If the statement returns no rows, an empty string is returned.
        """
        async with self._async_engine.begin() as connection:
            if self._schema is not None:
                if self.dialect == "snowflake":
                    await connection.exec_driver_sql(
                        f"ALTER SESSION SET search_path='{self._schema}'"
                    )
                elif self.dialect == "bigquery":
                    await connection.exec_driver_sql(
                        f"SET @@dataset_id='{self._schema}'"
                    )
                else:
                    await connection.exec_driver_sql(
                        f"SET search_path TO {self._schema}"
                    )
            cursor = await connection.execute(text(command))
            if cursor.returns_rows:
                if fetch == "all":
                    result = cursor.fetchall()
                elif fetch == "one":
                    result = cursor.fetchone()[0]  # type: ignore
                else:
                    raise ValueError("Fetch parameter must be either 'one' or 'all'")
                return str(result)
        return ""

    @classmethod
    def from_uri(
        cls,
        database_uri: str,
        database_auri: str,
        engine_args: Optional[dict] = None,
        **kwargs: Any,
    ) -> SQLDatabase:
        """Construct a SQLAlchemy engine from URI."""
        _engine_args = engine_args or {}
        sync_engine = create_engine(database_uri, **_engine_args)
        async_engine = create_async_engine(database_auri, **_engine_args)
        return cls(sync_engine, async_engine, **kwargs)

    async def arun_no_throw(self, command: str, fetch: str = "all") -> str:
        """Execute a SQL command and return a string representing the results.

        If the statement returns rows, a string of the results is returned.
        If the statement returns no rows, an empty string is returned.

        If the statement throws an error, the error message is returned.
        """
        try:
            return await self.arun(command, fetch)
        except SQLAlchemyError as e:
            """Format the error message"""
            return f"Error: {e}"
