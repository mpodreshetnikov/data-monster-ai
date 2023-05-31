from langchain import SQLDatabase


import warnings
from typing import Any, Iterable, List, Optional

import sqlalchemy
from sqlalchemy import (
    MetaData,
    Table,
    create_engine,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import CursorResult, Engine
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.schema import CreateTable
import logging


def _format_index(index: sqlalchemy.engine.interfaces.ReflectedIndex) -> str:
    return (
        f'Name: {index["name"]}, Unique: {index["unique"]},'
        f' Columns: {str(index["column_names"])}'
    )


logger = logging.getLogger(__name__)


class MultischemaSQLDatabase(SQLDatabase):
    """SQLAlchemy wrapper around a database."""

    def __init__(
        self,
        engine: Engine,
        schema: Optional[str] = None,
        metadata: Optional[MetaData] = None,
        ignore_tables: Optional[List[str]] = None,
        include_tables: Optional[List[str]] = None,
        sample_rows_in_table_info: int = 3,
        indexes_in_table_info: bool = False,
        custom_table_info: Optional[dict] = None,
        view_support: bool = False,
    ):
        if schema:
            return super().__init__(
                engine, schema, metadata, ignore_tables, include_tables
            )

        self._schema = None
        self._engine = engine

        if include_tables and ignore_tables:
            raise ValueError("Cannot specify both include_tables and ignore_tables")

        self._inspector = inspect(self._engine)

        self._all_tables = set()
        all_schemas = self._inspector.get_schema_names()

        for schema in all_schemas:
            tables = self._inspector.get_table_names(schema=schema)
            views = (
                self._inspector.get_view_names(schema=schema) if view_support else []
            )
            self._all_tables.update(tables + views)

        if include_tables:
            self.included_schemas, self.included_tables = self.parse_table_names(
                include_tables
            )
        else:
            self.included_schemas, self.included_tables = set(), set()

        self._include_tables = self.included_tables if self.included_tables else set()
        self.validate_tables(self._include_tables, self._all_tables)

        if ignore_tables:
            self.ignore_schemas, self.ignore_tables = self.parse_table_names(
                ignore_tables
            )
        else:
            self.ignore_schemas, self.ignore_tables = set(), set()

        self._ignore_tables = self.ignore_tables if self.ignore_tables else set()
        self.validate_tables(self._ignore_tables, self._all_tables)

        usable_tables = self.get_usable_table_names()
        self._usable_tables = set(usable_tables) if usable_tables else self._all_tables

        if not isinstance(sample_rows_in_table_info, int):
            raise TypeError("sample_rows_in_table_info must be an integer")

        self._sample_rows_in_table_info = sample_rows_in_table_info
        self._indexes_in_table_info = indexes_in_table_info

        self._custom_table_info = custom_table_info
        if self._custom_table_info:
            if not isinstance(self._custom_table_info, dict):
                raise TypeError(
                    "table_info must be a dictionary with table names as keys and the "
                    "desired table info as values"
                )
            # only keep the tables that are also present in the database
            intersection = set(self._custom_table_info).intersection(self._all_tables)
            self._custom_table_info = {
                (table, self._custom_table_info[table])
                for table in self._custom_table_info
                if table in intersection
            }

        self._metadata = metadata or MetaData()

        self.reflect_tables_in_metadata(view_support)

    def reflect_tables_in_metadata(self, view_support: bool):
        """
        Функция выполняет отражение таблиц в метаданных на основе списка usable_tables.

        Args:
            view_support (bool): Флаг, указывающий поддержку представлений.

        Raises:
            ValueError: Если найдено более одной схемы для таблицы или если схема не найдена.

        """
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

    def parse_table_names(self, table_names):
        table_parts = (
            table_name.split(".") if "." in table_name else ("public", table_name)
            for table_name in table_names
        )
        schemas, tables = map(set, zip(*table_parts))
        return schemas, tables

    def validate_tables(self, tables, all_tables):
        if tables:
            if missing_tables := tables - all_tables:
                raise ValueError(f"Tables {missing_tables} not found in database")
