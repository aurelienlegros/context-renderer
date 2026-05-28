"""
metrics.py
~~~~~~~~~~
Computes column-level data statistics for MSSQL tables.

Per column:
  - Row count, null count, null rate
  - Distinct count & cardinality ratio
  - Min / Max (orderable types)
  - Average (numeric types)
  - Top N most frequent values
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .inspector import ColumnInfo, TableInfo


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ColumnMetrics:
    column_name: str
    data_type: str
    row_count: int
    null_count: int
    null_rate: float
    distinct_count: int
    cardinality_ratio: float
    min_value: Any = None
    max_value: Any = None
    avg_value: float | None = None
    top_values: list[tuple[Any, int]] = field(default_factory=list)


@dataclass
class TableMetrics:
    schema: str
    table_name: str
    row_count: int
    column_metrics: list[ColumnMetrics] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Type sets
# ---------------------------------------------------------------------------

_NUMERIC_TYPES = {
    "int", "bigint", "smallint", "tinyint",
    "decimal", "numeric", "float", "real",
    "money", "smallmoney",
}

_DATE_TYPES = {
    "date", "datetime", "datetime2",
    "smalldatetime", "datetimeoffset", "time",
}

_ORDERABLE_TYPES = _NUMERIC_TYPES | _DATE_TYPES | {
    "char", "varchar", "nvarchar", "nchar",
}


# ---------------------------------------------------------------------------
# DataMetrics
# ---------------------------------------------------------------------------


class DataMetrics:
    """
    Computes per-column statistics for a list of :class:`~.inspector.TableInfo` objects.

    Usage::

        metrics = DataMetrics(engine, top_n=5)

        # Single table
        tm = metrics.compute(table_info)

        # All tables in a schema
        all_tm = metrics.compute_all(schema.tables)
    """

    def __init__(self, engine: Engine, top_n: int = 5) -> None:
        self.engine = engine
        self.top_n = top_n

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def compute(self, table: TableInfo) -> TableMetrics:
        """Compute metrics for a single table."""
        with self.engine.connect() as conn:
            row_count = table.row_count or self._count_rows(conn, table.schema, table.name)
            col_metrics = [
                self._column_metrics(conn, table.schema, table.name, col, row_count)
                for col in table.columns
            ]
        return TableMetrics(
            schema=table.schema,
            table_name=table.name,
            row_count=row_count,
            column_metrics=col_metrics,
        )

    def compute_all(self, tables: list[TableInfo]) -> list[TableMetrics]:
        """Compute metrics for all tables (views are skipped)."""
        return [self.compute(t) for t in tables if t.table_type == "TABLE"]

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _count_rows(self, conn: Any, schema: str, table: str) -> int:
        return conn.execute(
            text(f"SELECT COUNT(*) FROM [{schema}].[{table}]")
        ).scalar() or 0

    def _column_metrics(
        self,
        conn: Any,
        schema: str,
        table: str,
        col: ColumnInfo,
        row_count: int,
    ) -> ColumnMetrics:
        fqt = f"[{schema}].[{table}]"
        fcol = f"[{col.name}]"

        # Null & distinct
        row = conn.execute(text(f"""
            SELECT
                SUM(CASE WHEN {fcol} IS NULL THEN 1 ELSE 0 END),
                COUNT(DISTINCT {fcol})
            FROM {fqt}
        """)).fetchone()
        null_count = int(row[0] or 0)
        distinct_count = int(row[1] or 0)
        null_rate = null_count / row_count if row_count else 0.0
        non_null = row_count - null_count
        cardinality_ratio = distinct_count / non_null if non_null > 0 else 0.0

        # Min / Max
        min_val = max_val = None
        if col.data_type.lower() in _ORDERABLE_TYPES:
            try:
                r = conn.execute(
                    text(f"SELECT MIN({fcol}), MAX({fcol}) FROM {fqt}")
                ).fetchone()
                min_val, max_val = r[0], r[1]
            except Exception:
                pass

        # Avg (numeric only)
        avg_val = None
        if col.data_type.lower() in _NUMERIC_TYPES:
            try:
                val = conn.execute(
                    text(f"SELECT AVG(CAST({fcol} AS FLOAT)) FROM {fqt}")
                ).scalar()
                avg_val = round(float(val), 4) if val is not None else None
            except Exception:
                pass

        # Top N values
        top_values: list[tuple[Any, int]] = []
        try:
            rows = conn.execute(text(f"""
                SELECT TOP {self.top_n} {fcol}, COUNT(*) AS cnt
                FROM {fqt}
                WHERE {fcol} IS NOT NULL
                GROUP BY {fcol}
                ORDER BY cnt DESC
            """)).fetchall()
            top_values = [(r[0], r[1]) for r in rows]
        except Exception:
            pass

        return ColumnMetrics(
            column_name=col.name,
            data_type=col.data_type,
            row_count=row_count,
            null_count=null_count,
            null_rate=round(null_rate, 4),
            distinct_count=distinct_count,
            cardinality_ratio=round(cardinality_ratio, 4),
            min_value=min_val,
            max_value=max_val,
            avg_value=avg_val,
            top_values=top_values,
        )
