from __future__ import annotations

import csv
import importlib
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from vsf_profiler.models import CatalogTable, ColumnSchema, CsvCatalog, ForeignKey, Schema, TableSchema


DEFAULT_POSTGRES_URL_ENV = "VSF_PROFILER_POSTGRES_URL"
DEFAULT_POSTGRES_SCHEMA = "public"
DEFAULT_POSTGRES_CHUNK_ROWS = 10_000
MAX_POSTGRES_CHUNK_ROWS = 100_000
DEFAULT_MYSQL_URL_ENV = "VSF_PROFILER_MYSQL_URL"
DEFAULT_MYSQL_SCHEMA = ""
DEFAULT_MYSQL_CHUNK_ROWS = 10_000
MAX_MYSQL_CHUNK_ROWS = 100_000
SENSITIVE_KEY_PARTS = ("secret", "token", "credential", "password", "api_key")


class TabularSourceConnector(Protocol):
    source_type: str

    def runtime_inputs(self) -> dict[str, Any]:
        ...

    def prepare_schema(self) -> tuple[Schema, dict[str, Any]]:
        ...

    def build_catalog(self, *, schema: Schema, out_dir: Path) -> tuple[CsvCatalog, dict[str, Any], list[Path]]:
        ...


@dataclass(frozen=True)
class PostgresTableRef:
    schema_name: str
    table_name: str
    output_name: str

    @property
    def source_name(self) -> str:
        return f"{self.schema_name}.{self.table_name}"


@dataclass(frozen=True)
class MySQLTableRef:
    schema_name: str
    table_name: str
    output_name: str

    @property
    def source_name(self) -> str:
        return f"{self.schema_name}.{self.table_name}"


@dataclass
class IntrospectedTable:
    ref: PostgresTableRef | MySQLTableRef
    columns: list[dict[str, Any]]
    primary_key: list[str] = field(default_factory=list)
    unique_constraints: list[list[str]] = field(default_factory=list)
    foreign_keys: list[dict[str, Any]] = field(default_factory=list)
    row_count_estimate: int | None = None


class PostgresConnector:
    source_type = "postgres"

    def __init__(
        self,
        *,
        connection_url: str,
        selected_tables: list[PostgresTableRef] | None = None,
        default_schema: str = DEFAULT_POSTGRES_SCHEMA,
        chunk_rows: int = DEFAULT_POSTGRES_CHUNK_ROWS,
        provided_by: str = "option",
    ) -> None:
        if not connection_url.strip():
            raise ValueError("Postgres connection URL is required.")
        if chunk_rows <= 0 or chunk_rows > MAX_POSTGRES_CHUNK_ROWS:
            raise ValueError(
                f"postgres chunk rows must be between 1 and {MAX_POSTGRES_CHUNK_ROWS}."
            )
        self.connection_url = connection_url
        self.selected_tables = selected_tables or []
        self.default_schema = default_schema or DEFAULT_POSTGRES_SCHEMA
        self.chunk_rows = chunk_rows
        self.provided_by = provided_by
        self._introspected_tables: list[IntrospectedTable] | None = None
        self._warnings: list[str] = []

    @classmethod
    def from_config(
        cls,
        *,
        postgres_url: str | None,
        postgres_url_env: str = DEFAULT_POSTGRES_URL_ENV,
        postgres_schema: str = DEFAULT_POSTGRES_SCHEMA,
        postgres_tables: str | None = None,
        postgres_chunk_rows: int = DEFAULT_POSTGRES_CHUNK_ROWS,
    ) -> PostgresConnector:
        url = postgres_url.strip() if postgres_url else ""
        provided_by = "option"
        if not url:
            provided_by = f"env:{postgres_url_env}"
            url = os.environ.get(postgres_url_env, "").strip()
        if not url:
            raise ValueError(
                f"Postgres URL was not provided. Use --postgres-url or set {postgres_url_env}."
            )
        return cls(
            connection_url=url,
            selected_tables=parse_postgres_tables(postgres_tables, default_schema=postgres_schema),
            default_schema=postgres_schema,
            chunk_rows=postgres_chunk_rows,
            provided_by=provided_by,
        )

    def runtime_inputs(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "postgres_url": redact_connection_url(self.connection_url),
            "postgres_url_provided_by": self.provided_by,
            "postgres_schema": self.default_schema,
            "postgres_tables": [table.source_name for table in self.selected_tables],
            "postgres_chunk_rows": self.chunk_rows,
        }

    def prepare_schema(self) -> tuple[Schema, dict[str, Any]]:
        tables = self._introspect_tables()
        schema = schema_from_postgres_introspection(tables)
        parse_report = _schema_parse_report_from_introspection(
            schema=schema,
            parser="vsf_profiler.postgres_introspection",
            warnings=self._warnings,
            construct="Postgres",
        )
        return schema, parse_report

    def build_catalog(self, *, schema: Schema, out_dir: Path) -> tuple[CsvCatalog, dict[str, Any], list[Path]]:
        tables = self._introspect_tables()
        extract_dir = out_dir / ".connector_extracts" / "postgres"
        extract_dir.mkdir(parents=True, exist_ok=True)
        catalog = CsvCatalog()
        metadata_tables: list[dict[str, Any]] = []

        conn = self._connect()
        try:
            for table in tables:
                if table.ref.output_name not in schema.tables:
                    catalog.extra_csvs.append(table.ref.output_name)
                extract_path = extract_dir / f"{_safe_extract_name(table.ref.output_name)}.csv"
                rows_exported = self._export_table(conn, table, extract_path)
                catalog.tables[table.ref.output_name] = CatalogTable(
                    table=table.ref.output_name,
                    csv_path=extract_path,
                    columns=[column["name"] for column in table.columns],
                    file_size_mb=round(extract_path.stat().st_size / (1024 * 1024), 4),
                    source_type="postgres",
                    source_name=f"postgres:{table.ref.source_name}",
                )
                metadata_tables.append(
                    {
                        "table": table.ref.output_name,
                        "source_table": table.ref.source_name,
                        "columns": [column["name"] for column in table.columns],
                        "column_count": len(table.columns),
                        "row_count_estimate": table.row_count_estimate,
                        "rows_extracted": rows_exported,
                        "status": "extracted",
                    }
                )
        finally:
            conn.close()

        for table_name in schema.tables:
            if table_name not in catalog.tables:
                catalog.missing_tables.append(table_name)

        metadata = {
            "artifact": "connector_metadata",
            "version": 1,
            "source_type": self.source_type,
            "connection": {
                "url": redact_connection_url(self.connection_url),
                "provided_by": self.provided_by,
            },
            "default_schema": self.default_schema,
            "introspection_status": "completed",
            "extraction_status": "completed",
            "tables_scanned": [table["table"] for table in metadata_tables],
            "tables": metadata_tables,
            "warnings": list(self._warnings),
            "chunk_rows": self.chunk_rows,
            "raw_extracts_persisted": False,
            "secrets_redacted": True,
        }
        return catalog, metadata, [extract_dir]

    def _introspect_tables(self) -> list[IntrospectedTable]:
        if self._introspected_tables is not None:
            return self._introspected_tables
        conn = self._connect()
        try:
            selected_tables = self.selected_tables or self._list_schema_tables(conn)
            if not selected_tables:
                raise ValueError(f"No Postgres tables found in schema {self.default_schema}.")
            self._introspected_tables = [
                self._introspect_table(conn, table_ref) for table_ref in selected_tables
            ]
        finally:
            conn.close()
        return self._introspected_tables

    def _connect(self):
        try:
            psycopg = importlib.import_module("psycopg")
        except ImportError as exc:
            raise RuntimeError(
                "Postgres connector requires psycopg. Install with "
                "`python -m pip install -e .[postgres]`."
            ) from exc
        try:
            return psycopg.connect(self.connection_url)
        except Exception as exc:
            raise RuntimeError(
                f"Could not connect to Postgres using {redact_connection_url(self.connection_url)}: "
                f"{redact_secret_text(str(exc))}"
            ) from exc

    def _list_schema_tables(self, conn) -> list[PostgresTableRef]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """,
                (self.default_schema,),
            )
            rows = cur.fetchall()
        return [
            PostgresTableRef(
                schema_name=schema_name,
                table_name=table_name,
                output_name=_output_table_name(schema_name, table_name, self.default_schema),
            )
            for schema_name, table_name in rows
        ]

    def _introspect_table(self, conn, table_ref: PostgresTableRef) -> IntrospectedTable:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, udt_name, is_nullable, ordinal_position
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (table_ref.schema_name, table_ref.table_name),
            )
            column_rows = cur.fetchall()
            if not column_rows:
                raise ValueError(f"Postgres table not found: {table_ref.source_name}")
            cur.execute(
                """
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.constraint_schema = kcu.constraint_schema
                WHERE tc.table_schema = %s
                  AND tc.table_name = %s
                  AND tc.constraint_type = 'PRIMARY KEY'
                ORDER BY kcu.ordinal_position
                """,
                (table_ref.schema_name, table_ref.table_name),
            )
            primary_key = [row[0] for row in cur.fetchall()]
            cur.execute(
                """
                SELECT tc.constraint_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.constraint_schema = kcu.constraint_schema
                WHERE tc.table_schema = %s
                  AND tc.table_name = %s
                  AND tc.constraint_type = 'UNIQUE'
                ORDER BY tc.constraint_name, kcu.ordinal_position
                """,
                (table_ref.schema_name, table_ref.table_name),
            )
            unique_constraints = _group_constraint_columns(cur.fetchall())
            cur.execute(
                """
                SELECT
                  tc.constraint_name,
                  kcu.column_name,
                  ccu.table_schema AS foreign_table_schema,
                  ccu.table_name AS foreign_table_name,
                  ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.constraint_schema = kcu.constraint_schema
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name
                 AND ccu.constraint_schema = tc.constraint_schema
                WHERE tc.table_schema = %s
                  AND tc.table_name = %s
                  AND tc.constraint_type = 'FOREIGN KEY'
                ORDER BY tc.constraint_name, kcu.ordinal_position
                """,
                (table_ref.schema_name, table_ref.table_name),
            )
            foreign_keys = _group_foreign_keys(cur.fetchall(), self.default_schema)
            cur.execute(
                """
                SELECT COALESCE(c.reltuples::bigint, -1)
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s AND c.relname = %s
                """,
                (table_ref.schema_name, table_ref.table_name),
            )
            estimate_row = cur.fetchone()

        return IntrospectedTable(
            ref=table_ref,
            columns=[
                {
                    "name": row[0],
                    "type": _postgres_type_to_dbml(row[1], row[2]),
                    "nullable": str(row[3]).upper() == "YES",
                    "ordinal_position": int(row[4]),
                }
                for row in column_rows
            ],
            primary_key=primary_key,
            unique_constraints=unique_constraints,
            foreign_keys=foreign_keys,
            row_count_estimate=(
                int(estimate_row[0])
                if estimate_row and estimate_row[0] is not None and int(estimate_row[0]) >= 0
                else None
            ),
        )

    def _export_table(self, conn, table: IntrospectedTable, extract_path: Path) -> int:
        column_names = [column["name"] for column in table.columns]
        sql = (
            f"SELECT {', '.join(_quote_pg_ident(column) for column in column_names)} "
            f"FROM {_quote_pg_ident(table.ref.schema_name)}.{_quote_pg_ident(table.ref.table_name)}"
        )
        rows_exported = 0
        with extract_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(column_names)
            try:
                cursor = conn.cursor(name=f"vsf_profile_{_safe_extract_name(table.ref.output_name)}")
            except TypeError:
                cursor = conn.cursor()
            try:
                cursor.execute(sql)
                while True:
                    rows = cursor.fetchmany(self.chunk_rows)
                    if not rows:
                        break
                    writer.writerows(rows)
                    rows_exported += len(rows)
            finally:
                cursor.close()
        return rows_exported


class MySQLConnector:
    source_type = "mysql"

    def __init__(
        self,
        *,
        connection_url: str,
        selected_tables: list[MySQLTableRef] | None = None,
        default_schema: str = DEFAULT_MYSQL_SCHEMA,
        chunk_rows: int = DEFAULT_MYSQL_CHUNK_ROWS,
        provided_by: str = "option",
    ) -> None:
        if not connection_url.strip():
            raise ValueError("MySQL connection URL is required.")
        if chunk_rows <= 0 or chunk_rows > MAX_MYSQL_CHUNK_ROWS:
            raise ValueError(f"mysql chunk rows must be between 1 and {MAX_MYSQL_CHUNK_ROWS}.")
        resolved_schema = default_schema.strip() or _mysql_database_from_url(connection_url)
        if not resolved_schema:
            raise ValueError("MySQL schema/database is required. Use --mysql-schema or a URL path.")
        self.connection_url = connection_url
        self.selected_tables = selected_tables or []
        self.default_schema = resolved_schema
        self.chunk_rows = chunk_rows
        self.provided_by = provided_by
        self._introspected_tables: list[IntrospectedTable] | None = None
        self._warnings: list[str] = []

    @classmethod
    def from_config(
        cls,
        *,
        mysql_url: str | None,
        mysql_url_env: str = DEFAULT_MYSQL_URL_ENV,
        mysql_schema: str = DEFAULT_MYSQL_SCHEMA,
        mysql_tables: str | None = None,
        mysql_chunk_rows: int = DEFAULT_MYSQL_CHUNK_ROWS,
    ) -> MySQLConnector:
        url = mysql_url.strip() if mysql_url else ""
        provided_by = "option"
        if not url:
            provided_by = f"env:{mysql_url_env}"
            url = os.environ.get(mysql_url_env, "").strip()
        if not url:
            raise ValueError(f"MySQL URL was not provided. Use --mysql-url or set {mysql_url_env}.")
        default_schema = mysql_schema.strip() or _mysql_database_from_url(url)
        return cls(
            connection_url=url,
            selected_tables=parse_mysql_tables(mysql_tables, default_schema=default_schema),
            default_schema=default_schema,
            chunk_rows=mysql_chunk_rows,
            provided_by=provided_by,
        )

    def runtime_inputs(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "mysql_url": redact_connection_url(self.connection_url),
            "mysql_url_provided_by": self.provided_by,
            "mysql_schema": self.default_schema,
            "mysql_tables": [table.source_name for table in self.selected_tables],
            "mysql_chunk_rows": self.chunk_rows,
        }

    def prepare_schema(self) -> tuple[Schema, dict[str, Any]]:
        tables = self._introspect_tables()
        schema = schema_from_mysql_introspection(tables)
        parse_report = _schema_parse_report_from_introspection(
            schema=schema,
            parser="vsf_profiler.mysql_introspection",
            warnings=self._warnings,
            construct="MySQL",
        )
        return schema, parse_report

    def build_catalog(self, *, schema: Schema, out_dir: Path) -> tuple[CsvCatalog, dict[str, Any], list[Path]]:
        tables = self._introspect_tables()
        extract_dir = out_dir / ".connector_extracts" / "mysql"
        extract_dir.mkdir(parents=True, exist_ok=True)
        catalog = CsvCatalog()
        metadata_tables: list[dict[str, Any]] = []

        conn = self._connect()
        try:
            for table in tables:
                if table.ref.output_name not in schema.tables:
                    catalog.extra_csvs.append(table.ref.output_name)
                extract_path = extract_dir / f"{_safe_extract_name(table.ref.output_name)}.csv"
                rows_exported = self._export_table(conn, table, extract_path)
                catalog.tables[table.ref.output_name] = CatalogTable(
                    table=table.ref.output_name,
                    csv_path=extract_path,
                    columns=[column["name"] for column in table.columns],
                    file_size_mb=round(extract_path.stat().st_size / (1024 * 1024), 4),
                    source_type="mysql",
                    source_name=f"mysql:{table.ref.source_name}",
                )
                metadata_tables.append(
                    {
                        "table": table.ref.output_name,
                        "source_table": table.ref.source_name,
                        "columns": [column["name"] for column in table.columns],
                        "column_count": len(table.columns),
                        "row_count_estimate": table.row_count_estimate,
                        "rows_extracted": rows_exported,
                        "status": "extracted",
                    }
                )
        finally:
            conn.close()

        for table_name in schema.tables:
            if table_name not in catalog.tables:
                catalog.missing_tables.append(table_name)

        metadata = {
            "artifact": "connector_metadata",
            "version": 1,
            "source_type": self.source_type,
            "connection": {
                "url": redact_connection_url(self.connection_url),
                "provided_by": self.provided_by,
            },
            "default_schema": self.default_schema,
            "introspection_status": "completed",
            "extraction_status": "completed",
            "tables_scanned": [table["table"] for table in metadata_tables],
            "tables": metadata_tables,
            "warnings": list(self._warnings),
            "chunk_rows": self.chunk_rows,
            "raw_extracts_persisted": False,
            "secrets_redacted": True,
        }
        return catalog, metadata, [extract_dir]

    def _introspect_tables(self) -> list[IntrospectedTable]:
        if self._introspected_tables is not None:
            return self._introspected_tables
        conn = self._connect()
        try:
            selected_tables = self.selected_tables or self._list_schema_tables(conn)
            if not selected_tables:
                raise ValueError(f"No MySQL tables found in schema/database {self.default_schema}.")
            self._introspected_tables = [
                self._introspect_table(conn, table_ref) for table_ref in selected_tables
            ]
        finally:
            conn.close()
        return self._introspected_tables

    def _connect(self):
        try:
            pymysql = importlib.import_module("pymysql")
        except ImportError as exc:
            raise RuntimeError(
                "MySQL connector requires PyMySQL. Install with "
                "`python -m pip install -e .[mysql]`."
            ) from exc
        try:
            connection_kwargs = _mysql_connection_kwargs(self.connection_url, self.default_schema)
            return pymysql.connect(**connection_kwargs)
        except Exception as exc:
            raise RuntimeError(
                f"Could not connect to MySQL using {redact_connection_url(self.connection_url)}: "
                f"{redact_secret_text(str(exc))}"
            ) from exc

    def _list_schema_tables(self, conn) -> list[MySQLTableRef]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """,
                (self.default_schema,),
            )
            rows = cur.fetchall()
        return [
            MySQLTableRef(
                schema_name=schema_name,
                table_name=table_name,
                output_name=_output_table_name(schema_name, table_name, self.default_schema),
            )
            for schema_name, table_name in rows
        ]

    def _introspect_table(self, conn, table_ref: MySQLTableRef) -> IntrospectedTable:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, column_type, is_nullable, ordinal_position
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (table_ref.schema_name, table_ref.table_name),
            )
            column_rows = cur.fetchall()
            if not column_rows:
                raise ValueError(f"MySQL table not found: {table_ref.source_name}")
            cur.execute(
                """
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_schema = kcu.constraint_schema
                 AND tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                 AND tc.table_name = kcu.table_name
                WHERE tc.table_schema = %s
                  AND tc.table_name = %s
                  AND tc.constraint_type = 'PRIMARY KEY'
                ORDER BY kcu.ordinal_position
                """,
                (table_ref.schema_name, table_ref.table_name),
            )
            primary_key = [row[0] for row in cur.fetchall()]
            cur.execute(
                """
                SELECT tc.constraint_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_schema = kcu.constraint_schema
                 AND tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                 AND tc.table_name = kcu.table_name
                WHERE tc.table_schema = %s
                  AND tc.table_name = %s
                  AND tc.constraint_type = 'UNIQUE'
                ORDER BY tc.constraint_name, kcu.ordinal_position
                """,
                (table_ref.schema_name, table_ref.table_name),
            )
            unique_constraints = _group_constraint_columns(cur.fetchall())
            cur.execute(
                """
                SELECT
                  rc.constraint_name,
                  kcu.column_name,
                  kcu.referenced_table_schema,
                  kcu.referenced_table_name,
                  kcu.referenced_column_name
                FROM information_schema.referential_constraints rc
                JOIN information_schema.key_column_usage kcu
                  ON rc.constraint_schema = kcu.constraint_schema
                 AND rc.constraint_name = kcu.constraint_name
                 AND rc.table_name = kcu.table_name
                WHERE kcu.table_schema = %s
                  AND kcu.table_name = %s
                  AND kcu.referenced_table_name IS NOT NULL
                ORDER BY rc.constraint_name, kcu.ordinal_position
                """,
                (table_ref.schema_name, table_ref.table_name),
            )
            foreign_keys = _group_foreign_keys(cur.fetchall(), self.default_schema)
            cur.execute(
                """
                SELECT table_rows
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
                """,
                (table_ref.schema_name, table_ref.table_name),
            )
            estimate_row = cur.fetchone()

        return IntrospectedTable(
            ref=table_ref,
            columns=[
                {
                    "name": row[0],
                    "type": _mysql_type_to_dbml(row[1], row[2]),
                    "nullable": str(row[3]).upper() == "YES",
                    "ordinal_position": int(row[4]),
                }
                for row in column_rows
            ],
            primary_key=primary_key,
            unique_constraints=unique_constraints,
            foreign_keys=foreign_keys,
            row_count_estimate=(
                int(estimate_row[0])
                if estimate_row and estimate_row[0] is not None and int(estimate_row[0]) >= 0
                else None
            ),
        )

    def _export_table(self, conn, table: IntrospectedTable, extract_path: Path) -> int:
        column_names = [column["name"] for column in table.columns]
        sql = (
            f"SELECT {', '.join(_quote_mysql_ident(column) for column in column_names)} "
            f"FROM {_quote_mysql_ident(table.ref.schema_name)}."
            f"{_quote_mysql_ident(table.ref.table_name)}"
        )
        rows_exported = 0
        with extract_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(column_names)
            try:
                pymysql = importlib.import_module("pymysql")
                cursor = conn.cursor(pymysql.cursors.SSCursor)
            except TypeError:
                cursor = conn.cursor()
            try:
                cursor.execute(sql)
                while True:
                    rows = cursor.fetchmany(self.chunk_rows)
                    if not rows:
                        break
                    writer.writerows(rows)
                    rows_exported += len(rows)
            finally:
                cursor.close()
        return rows_exported


def parse_postgres_tables(
    value: str | None,
    *,
    default_schema: str = DEFAULT_POSTGRES_SCHEMA,
) -> list[PostgresTableRef]:
    if not value or not value.strip():
        return []
    refs = []
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        pieces = [_strip_identifier_quotes(piece) for piece in part.split(".") if piece.strip()]
        if len(pieces) == 1:
            schema_name = default_schema
            table_name = pieces[0]
        elif len(pieces) == 2:
            schema_name, table_name = pieces
        else:
            raise ValueError(f"Postgres table must be table or schema.table: {part}")
        refs.append(
            PostgresTableRef(
                schema_name=schema_name,
                table_name=table_name,
                output_name=_output_table_name(schema_name, table_name, default_schema),
            )
        )
    return refs


def parse_mysql_tables(
    value: str | None,
    *,
    default_schema: str = DEFAULT_MYSQL_SCHEMA,
) -> list[MySQLTableRef]:
    if not value or not value.strip():
        return []
    if not default_schema:
        raise ValueError("MySQL schema/database is required when selecting unqualified tables.")
    refs = []
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        pieces = [_strip_identifier_quotes(piece) for piece in part.split(".") if piece.strip()]
        if len(pieces) == 1:
            schema_name = default_schema
            table_name = pieces[0]
        elif len(pieces) == 2:
            schema_name, table_name = pieces
        else:
            raise ValueError(f"MySQL table must be table or schema.table: {part}")
        refs.append(
            MySQLTableRef(
                schema_name=schema_name,
                table_name=table_name,
                output_name=_output_table_name(schema_name, table_name, default_schema),
            )
        )
    return refs


def schema_from_postgres_introspection(tables: list[IntrospectedTable]) -> Schema:
    return _schema_from_connector_introspection(tables)


def schema_from_mysql_introspection(tables: list[IntrospectedTable]) -> Schema:
    return _schema_from_connector_introspection(tables)


def _schema_from_connector_introspection(tables: list[IntrospectedTable]) -> Schema:
    schema = Schema()
    for table in tables:
        table_schema = TableSchema(name=table.ref.output_name)
        for column in table.columns:
            column_schema = ColumnSchema(
                name=column["name"],
                type=column["type"],
                not_null=not bool(column["nullable"]),
                is_pk=column["name"] in table.primary_key,
                unique=any([column["name"]] == constraint for constraint in table.unique_constraints),
            )
            if column_schema.is_pk:
                column_schema.not_null = True
            table_schema.columns[column_schema.name] = column_schema
        table_schema.primary_key = list(table.primary_key)
        table_schema.unique_constraints = [
            list(columns) for columns in table.unique_constraints if len(columns) > 1
        ]
        schema.tables[table.ref.output_name] = table_schema

    for table in tables:
        child_schema = schema.tables[table.ref.output_name]
        for fk in table.foreign_keys:
            parent_table = fk["parent_table"]
            rel = _relationship_from_fk(table.ref.output_name, parent_table, fk)
            schema.relationships.append(rel)
            for child_column, parent_column in zip(
                rel.child_columns,
                rel.parent_columns,
                strict=False,
            ):
                if child_column in child_schema.columns:
                    child_schema.columns[child_column].foreign_key = ForeignKey(
                        parent_table=rel.parent_table,
                        parent_column=parent_column,
                    )
    return schema


def _schema_parse_report_from_introspection(
    *,
    schema: Schema,
    parser: str,
    warnings: list[str],
    construct: str,
) -> dict[str, Any]:
    return {
        "artifact": "schema_parse_report",
        "version": 1,
        "parser": parser,
        "status": "generated_from_connector",
        "source": {"path": ""},
        "counts": {
            "projects": 0,
            "enums": 0,
            "enum_values": 0,
            "table_groups": 0,
            "tables": len(schema.tables),
            "columns": sum(len(table.columns) for table in schema.tables.values()),
            "indexes": sum(len(table.primary_key) > 0 for table in schema.tables.values())
            + sum(len(table.unique_constraints) for table in schema.tables.values()),
            "primary_indexes": sum(1 for table in schema.tables.values() if table.primary_key),
            "unique_indexes": sum(len(table.unique_constraints) for table in schema.tables.values()),
            "composite_primary_indexes": sum(
                1 for table in schema.tables.values() if len(table.primary_key) > 1
            ),
            "composite_unique_indexes": sum(
                1
                for table in schema.tables.values()
                for columns in table.unique_constraints
                if len(columns) > 1
            ),
            "relationships": len(schema.relationships),
            "inline_refs": 0,
            "ref_blocks": 0,
            "notes": 0,
            "defaults": 0,
            "settings": 0,
            "warnings": len(warnings),
            "errors": 0,
            "unsupported_constructs": 0,
        },
        "diagnostics": [
            {
                "severity": "warning",
                "code": f"{construct.upper()}_INTROSPECTION_WARNING",
                "message": warning,
                "line": None,
                "construct": construct,
                "snippet": "",
            }
            for warning in warnings
        ],
        "unsupported_constructs": [],
        "objects": {
            "projects": [],
            "enums": [],
            "table_groups": [],
            "tables": [
                {
                    "name": table.name,
                    "columns": list(table.columns),
                    "primary_key": list(table.primary_key),
                    "unique_constraints": list(table.unique_constraints),
                }
                for table in schema.tables.values()
            ],
        },
    }


def cleanup_connector_extracts(paths: list[Path]) -> None:
    for path in paths:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        parent = path.parent
        while parent.name == ".connector_extracts" or parent.parent.name == ".connector_extracts":
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


def connector_metadata_for_csv() -> dict[str, Any] | None:
    return None


def redact_connection_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return redact_secret_text(url)
    if not parsed.scheme or not parsed.netloc:
        return redact_secret_text(url)
    host = parsed.netloc.rsplit("@", 1)[1] if "@" in parsed.netloc else parsed.netloc
    return urlunsplit(
        (
            parsed.scheme,
            f"[redacted]@{host}",
            parsed.path,
            _redact_query(parsed.query),
            redact_secret_text(parsed.fragment),
        )
    )


def redact_secret_text(value: str) -> str:
    redacted = re.sub(
        r"(?i)((?:postgres(?:ql)?|mysql|mariadb|mysql\+pymysql|mariadb\+pymysql)://)([^@\s<>\"]+)@",
        r"\1[redacted]@",
        value,
    )
    redacted = re.sub(
        r"(?i)(password|passwd|pwd|token|api[_-]?key|secret)=([^\s,;&]+)",
        r"\1=[redacted]",
        redacted,
    )
    return redacted


def _redact_query(query: str) -> str:
    if not query:
        return ""
    pairs = parse_qsl(query, keep_blank_values=True)
    if not pairs:
        return redact_secret_text(query)
    redacted_pairs = []
    for key, value in pairs:
        if any(part in key.lower() for part in SENSITIVE_KEY_PARTS):
            redacted_pairs.append((key, "[redacted]"))
        else:
            redacted_pairs.append((key, redact_secret_text(value)))
    return urlencode(redacted_pairs)


def _relationship_from_fk(child_table: str, parent_table: str, fk: dict[str, Any]):
    from vsf_profiler.models import Relationship

    return Relationship(
        child_table=child_table,
        child_column=fk["child_columns"][0],
        child_columns=fk["child_columns"],
        parent_table=parent_table,
        parent_column=fk["parent_columns"][0],
        parent_columns=fk["parent_columns"],
        dbml_operator=">",
        declared_cardinality="MANY_TO_ONE",
        relationship_type="explicit_fk",
    )


def _group_constraint_columns(rows: list[tuple[Any, ...]]) -> list[list[str]]:
    grouped: dict[str, list[str]] = {}
    for constraint_name, column_name in rows:
        grouped.setdefault(str(constraint_name), []).append(str(column_name))
    return list(grouped.values())


def _group_foreign_keys(rows: list[tuple[Any, ...]], default_schema: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for constraint_name, child_column, parent_schema, parent_table, parent_column in rows:
        item = grouped.setdefault(
            str(constraint_name),
            {
                "child_columns": [],
                "parent_schema": str(parent_schema),
                "parent_source_table": str(parent_table),
                "parent_table": _output_table_name(
                    str(parent_schema),
                    str(parent_table),
                    default_schema,
                ),
                "parent_columns": [],
            },
        )
        item["child_columns"].append(str(child_column))
        item["parent_columns"].append(str(parent_column))
    return list(grouped.values())


def _postgres_type_to_dbml(data_type: str, udt_name: str) -> str:
    normalized = (data_type or udt_name or "").lower()
    if normalized in {"integer", "bigint", "smallint", "serial", "bigserial"}:
        return "int"
    if normalized in {"numeric", "decimal", "double precision", "real"}:
        return "float"
    if normalized in {"timestamp without time zone", "timestamp with time zone", "date"}:
        return "timestamp"
    if normalized == "boolean":
        return "boolean"
    return "varchar"


def _mysql_type_to_dbml(data_type: str, column_type: str) -> str:
    normalized = (data_type or "").lower()
    column_type_normalized = (column_type or "").lower()
    if normalized in {
        "tinyint",
        "smallint",
        "mediumint",
        "int",
        "integer",
        "bigint",
        "year",
    }:
        if normalized == "tinyint" and column_type_normalized.startswith("tinyint(1)"):
            return "boolean"
        return "int"
    if normalized in {"decimal", "numeric", "float", "double", "real"}:
        return "float"
    if normalized in {"timestamp", "datetime", "date", "time"}:
        return "timestamp"
    if normalized in {"bool", "boolean", "bit"}:
        return "boolean"
    if normalized == "json":
        return "json"
    return "varchar"


def _mysql_connection_kwargs(connection_url: str, default_schema: str) -> dict[str, Any]:
    try:
        parsed = urlsplit(connection_url)
    except ValueError as exc:
        raise ValueError("MySQL URL is invalid.") from exc
    scheme = parsed.scheme.lower()
    if scheme not in {"mysql", "mariadb", "mysql+pymysql", "mariadb+pymysql"}:
        raise ValueError("MySQL URL scheme must be mysql:// or mariadb://.")
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    database = default_schema or _mysql_database_from_url(connection_url)
    if not database:
        raise ValueError("MySQL schema/database is required. Use --mysql-schema or a URL path.")
    kwargs: dict[str, Any] = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": database,
        "charset": query.get("charset", "utf8mb4") or "utf8mb4",
        "autocommit": True,
    }
    if "unix_socket" in query and query["unix_socket"]:
        kwargs["unix_socket"] = query["unix_socket"]
    if query.get("ssl_disabled", "").lower() in {"1", "true", "yes"}:
        kwargs["ssl_disabled"] = True
    if "connect_timeout" in query and query["connect_timeout"]:
        try:
            kwargs["connect_timeout"] = int(query["connect_timeout"])
        except ValueError as exc:
            raise ValueError("MySQL connect_timeout must be an integer.") from exc
    return kwargs


def _mysql_database_from_url(connection_url: str) -> str:
    try:
        parsed = urlsplit(connection_url)
    except ValueError:
        return ""
    path = parsed.path.lstrip("/")
    if not path:
        return ""
    return unquote(path.split("/", 1)[0])


def _output_table_name(schema_name: str, table_name: str, default_schema: str) -> str:
    if schema_name == default_schema:
        return table_name
    return f"{schema_name}.{table_name}"


def _quote_pg_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _quote_mysql_ident(identifier: str) -> str:
    return "`" + identifier.replace("`", "``") + "`"


def _strip_identifier_quotes(identifier: str) -> str:
    stripped = identifier.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "`"}:
        return stripped[1:-1].replace(stripped[0] * 2, stripped[0])
    return stripped.strip('"` ')


def _safe_extract_name(table_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", table_name).strip("._") or "table"
