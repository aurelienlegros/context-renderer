"""
inspector.py
~~~~~~~~~~~~
Extracts structural metadata from a MSSQL database.

Covers:
  - Schemas (non-system)
  - Tables & Views
  - Columns (type, max_length, nullability, default, PK flag)
  - Primary Keys
  - Foreign Keys (cross-table relations)
  - Indexes (name, columns, unique flag)
  - Stored Procedures & Functions (name + definition snippet)
  - Row counts (via sys.partitions — fast, no full scan)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    max_length: int | None
    is_nullable: bool
    default_value: str | None
    is_primary_key: bool = False


@dataclass
class ForeignKeyInfo:
    constraint_name: str
    column: str
    referenced_schema: str
    referenced_table: str
    referenced_column: str


@dataclass
class IndexInfo:
    name: str
    columns: list[str]
    is_unique: bool
    is_primary_key: bool


@dataclass
class TableInfo:
    schema: str
    name: str
    table_type: str  # "TABLE" or "VIEW"
    columns: list[ColumnInfo] = field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = field(default_factory=list)
    indexes: list[IndexInfo] = field(default_factory=list)
    row_count: int | None = None

    @property
    def full_name(self) -> str:
        return f"{self.schema}.{self.name}"

    @property
    def primary_key_columns(self) -> list[str]:
        return [c.name for c in self.columns if c.is_primary_key]


@dataclass
class RoutineInfo:
    schema: str
    name: str
    routine_type: str          # "PROCEDURE" or "FUNCTION"
    definition_snippet: str    # First 500 chars of the definition


@dataclass
class DatabaseSchema:
    database_name: str
    schemas: list[str]
    tables: list[TableInfo]
    routines: list[RoutineInfo]


# ---------------------------------------------------------------------------
# Inspector
# ---------------------------------------------------------------------------

_SYSTEM_SCHEMAS = {
    "sys", "guest", "INFORMATION_SCHEMA",
    "db_owner", "db_accessadmin", "db_securityadmin", "db_ddladmin",
    "db_backupoperator", "db_datareader", "db_datawriter",
    "db_denydatareader", "db_denydatawriter",
}


class DatabaseInspector:
    """
    Inspects a MSSQL database and returns a :class:`DatabaseSchema`.

    Usage::

        inspector = DatabaseInspector(engine)
        schema = inspector.inspect()                    # all schemas
        schema = inspector.inspect(schemas=["dbo"])     # filtered
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def inspect(self, schemas: list[str] | None = None, verbose: bool = True) -> DatabaseSchema:
        """
        Run a full inspection of the database.

        Args:
            schemas: Limit to these schemas. ``None`` = all non-system schemas.
            verbose: Print progress to stdout.
        """
        with self.engine.connect() as conn:
            db_name = self._get_database_name(conn)
            all_schemas = self._get_schemas(conn)
            target_schemas = schemas or all_schemas

            tables = self._get_tables(conn, target_schemas)
            total = len(tables)
            if verbose:
                print(f"[inspect] {db_name} — {total} tables/views found, processing...")

            for i, table in enumerate(tables, 1):
                if verbose:
                    print(f"  [{i}/{total}] {table.schema}.{table.name}", flush=True)
                table.columns = self._get_columns(conn, table.schema, table.name)
                table.foreign_keys = self._get_foreign_keys(conn, table.schema, table.name)
                table.indexes = self._get_indexes(conn, table.schema, table.name)
                if table.table_type == "TABLE":
                    table.row_count = self._get_row_count(conn, table.schema, table.name)

            routines = self._get_routines(conn, target_schemas)

        if verbose:
            print(f"[inspect] Done — {total} tables/views, {len(routines)} routines.")

        return DatabaseSchema(
            database_name=db_name,
            schemas=all_schemas,
            tables=tables,
            routines=routines,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def _get_database_name(self, conn: Any) -> str:
        return conn.execute(text("SELECT DB_NAME()")).scalar()

    def _get_schemas(self, conn: Any) -> list[str]:
        excluded = ", ".join(f"'{s}'" for s in _SYSTEM_SCHEMAS)
        rows = conn.execute(text(f"""
            SELECT name FROM sys.schemas
            WHERE name NOT IN ({excluded})
            ORDER BY name
        """)).fetchall()
        return [r[0] for r in rows]

    def _get_tables(self, conn: Any, schemas: list[str]) -> list[TableInfo]:
        placeholders = ", ".join(f"'{s}'" for s in schemas)
        rows = conn.execute(text(f"""
            SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA IN ({placeholders})
            ORDER BY TABLE_SCHEMA, TABLE_TYPE DESC, TABLE_NAME
        """)).fetchall()
        return [TableInfo(schema=r[0], name=r[1], table_type=r[2]) for r in rows]

    def _get_columns(self, conn: Any, schema: str, table: str) -> list[ColumnInfo]:
        rows = conn.execute(text("""
            SELECT
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.CHARACTER_MAXIMUM_LENGTH,
                c.IS_NULLABLE,
                c.COLUMN_DEFAULT,
                CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS IS_PK
            FROM INFORMATION_SCHEMA.COLUMNS c
            LEFT JOIN (
                SELECT ku.COLUMN_NAME
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                    ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                   AND tc.TABLE_SCHEMA    = ku.TABLE_SCHEMA
                   AND tc.TABLE_NAME      = ku.TABLE_NAME
                WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                  AND tc.TABLE_SCHEMA    = :schema
                  AND tc.TABLE_NAME      = :table
            ) pk ON c.COLUMN_NAME = pk.COLUMN_NAME
            WHERE c.TABLE_SCHEMA = :schema AND c.TABLE_NAME = :table
            ORDER BY c.ORDINAL_POSITION
        """), {"schema": schema, "table": table}).fetchall()

        return [
            ColumnInfo(
                name=r[0],
                data_type=r[1],
                max_length=r[2],
                is_nullable=(r[3] == "YES"),
                default_value=r[4],
                is_primary_key=bool(r[5]),
            )
            for r in rows
        ]

    def _get_foreign_keys(self, conn: Any, schema: str, table: str) -> list[ForeignKeyInfo]:
        rows = conn.execute(text("""
            SELECT
                fk.name        AS constraint_name,
                cp.name        AS column_name,
                rs.name        AS ref_schema,
                rt.name        AS ref_table,
                cr.name        AS ref_column
            FROM sys.foreign_keys fk
            JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            JOIN sys.columns cp ON fkc.parent_object_id   = cp.object_id
                                AND fkc.parent_column_id  = cp.column_id
            JOIN sys.columns cr ON fkc.referenced_object_id  = cr.object_id
                                AND fkc.referenced_column_id = cr.column_id
            JOIN sys.tables  rt ON fkc.referenced_object_id = rt.object_id
            JOIN sys.schemas rs ON rt.schema_id = rs.schema_id
            JOIN sys.tables  pt ON fkc.parent_object_id = pt.object_id
            JOIN sys.schemas ps ON pt.schema_id = ps.schema_id
            WHERE ps.name = :schema AND pt.name = :table
        """), {"schema": schema, "table": table}).fetchall()

        return [
            ForeignKeyInfo(
                constraint_name=r[0],
                column=r[1],
                referenced_schema=r[2],
                referenced_table=r[3],
                referenced_column=r[4],
            )
            for r in rows
        ]

    def _get_indexes(self, conn: Any, schema: str, table: str) -> list[IndexInfo]:
        rows = conn.execute(text("""
            SELECT
                i.name AS index_name,
                STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS cols,
                i.is_unique,
                i.is_primary_key
            FROM sys.indexes i
            JOIN sys.index_columns ic ON i.object_id  = ic.object_id
                                      AND i.index_id  = ic.index_id
            JOIN sys.columns c        ON ic.object_id = c.object_id
                                      AND ic.column_id = c.column_id
            JOIN sys.tables t         ON i.object_id  = t.object_id
            JOIN sys.schemas s        ON t.schema_id  = s.schema_id
            WHERE s.name = :schema AND t.name = :table
              AND i.name IS NOT NULL
            GROUP BY i.name, i.is_unique, i.is_primary_key
        """), {"schema": schema, "table": table}).fetchall()

        return [
            IndexInfo(
                name=r[0],
                columns=[c.strip() for c in r[1].split(",")],
                is_unique=bool(r[2]),
                is_primary_key=bool(r[3]),
            )
            for r in rows
        ]

    def _get_row_count(self, conn: Any, schema: str, table: str) -> int:
        """Fast row count via sys.partitions (no full scan)."""
        result = conn.execute(text("""
            SELECT SUM(p.rows)
            FROM sys.partitions p
            JOIN sys.tables t  ON p.object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = :schema AND t.name = :table
              AND p.index_id IN (0, 1)
        """), {"schema": schema, "table": table}).scalar()
        return int(result) if result is not None else 0

    def _get_routines(self, conn: Any, schemas: list[str]) -> list[RoutineInfo]:
        placeholders = ", ".join(f"'{s}'" for s in schemas)
        rows = conn.execute(text(f"""
            SELECT
                ROUTINE_SCHEMA,
                ROUTINE_NAME,
                ROUTINE_TYPE,
                LEFT(ROUTINE_DEFINITION, 500) AS snippet
            FROM INFORMATION_SCHEMA.ROUTINES
            WHERE ROUTINE_SCHEMA IN ({placeholders})
            ORDER BY ROUTINE_SCHEMA, ROUTINE_TYPE, ROUTINE_NAME
        """)).fetchall()

        return [
            RoutineInfo(
                schema=r[0],
                name=r[1],
                routine_type=r[2],
                definition_snippet=r[3] or "",
            )
            for r in rows
        ]
