"""
renderer.py
~~~~~~~~~~~
Renders structured Markdown context sheets from a DatabaseSchema + optional TableMetrics.

Output per database:
  - ``00_database_overview.md``  — global summary, table list, FK relation map, routines
  - ``{schema}__{table}.md``     — one file per table/view with full column detail
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .inspector import DatabaseSchema, TableInfo
from .metrics import TableMetrics


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _v(val: Any) -> str:
    """Format a value for Markdown tables — returns em-dash for None."""
    return "—" if val is None else str(val)


def _pct(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def _nullable(flag: bool) -> str:
    return "✓" if flag else "✗"


# ---------------------------------------------------------------------------
# ContextSheetRenderer
# ---------------------------------------------------------------------------


class ContextSheetRenderer:
    """
    Generates Markdown context sheets from a :class:`~.inspector.DatabaseSchema`
    and optional :class:`~.metrics.TableMetrics` list.

    Usage::

        renderer = ContextSheetRenderer(schema, table_metrics)

        # Get all sheets as {filename: markdown}
        sheets = renderer.render_all()

        # Save to disk
        paths = renderer.save("./output/MyDatabase")
    """

    def __init__(
        self,
        schema: DatabaseSchema,
        table_metrics: Optional[list[TableMetrics]] = None,
    ) -> None:
        self.schema = schema
        # Build a lookup {schema.table → TableMetrics}
        self._metrics: dict[str, TableMetrics] = {}
        if table_metrics:
            for tm in table_metrics:
                self._metrics[f"{tm.schema}.{tm.table_name}"] = tm

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def render_all(self) -> dict[str, str]:
        """Return all context sheets as ``{filename: markdown_content}``."""
        sheets: dict[str, str] = {
            "00_database_overview.md": self._render_overview(),
        }
        for table in self.schema.tables:
            filename = f"{table.schema}__{table.name}.md"
            sheets[filename] = self._render_table(table)
        return sheets

    def save(self, output_dir: str = "./output") -> list[str]:
        """Save all sheets to *output_dir* and return the written file paths."""
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        sheets = self.render_all()
        written: list[str] = []
        for filename, content in sheets.items():
            fp = root / filename
            fp.write_text(content, encoding="utf-8")
            written.append(str(fp))
        return written

    # ------------------------------------------------------------------
    # Overview sheet
    # ------------------------------------------------------------------

    def _render_overview(self) -> str:
        db = self.schema
        tables = [t for t in db.tables if t.table_type == "TABLE"]
        views  = [t for t in db.tables if t.table_type == "VIEW"]
        procs  = [r for r in db.routines if r.routine_type == "PROCEDURE"]
        funcs  = [r for r in db.routines if r.routine_type == "FUNCTION"]

        lines = [
            f"# Database Overview — `{db.database_name}`",
            "",
            "## Summary",
            "",
            "| Property | Value |",
            "|---|---|",
            f"| Database | `{db.database_name}` |",
            f"| Schemas | {', '.join(f'`{s}`' for s in db.schemas)} |",
            f"| Tables | {len(tables)} |",
            f"| Views | {len(views)} |",
            f"| Stored Procedures | {len(procs)} |",
            f"| Functions | {len(funcs)} |",
            "",
        ]

        # Tables
        lines += [
            "## Tables",
            "",
            "| Schema | Table | Columns | Rows | Primary Key |",
            "|---|---|---|---|---|",
        ]
        for t in tables:
            pk = ", ".join(f"`{c}`" for c in t.primary_key_columns) or "—"
            rows = f"{t.row_count:,}" if t.row_count is not None else "—"
            lines.append(
                f"| `{t.schema}` | [`{t.name}`](./{t.schema}__{t.name}.md)"
                f" | {len(t.columns)} | {rows} | {pk} |"
            )

        # Views
        if views:
            lines += [
                "",
                "## Views",
                "",
                "| Schema | View | Columns |",
                "|---|---|---|",
            ]
            for v in views:
                lines.append(
                    f"| `{v.schema}` | [`{v.name}`](./{v.schema}__{v.name}.md)"
                    f" | {len(v.columns)} |"
                )

        # Foreign key relations
        lines += ["", "## Foreign Key Relations", ""]
        fk_rows = [
            f"- `{t.schema}.{t.name}.{fk.column}` → "
            f"`{fk.referenced_schema}.{fk.referenced_table}.{fk.referenced_column}`"
            for t in tables
            for fk in t.foreign_keys
        ]
        lines += fk_rows if fk_rows else ["_No foreign keys found._"]

        # Routines
        if db.routines:
            lines += ["", "## Stored Procedures & Functions", ""]
            for r in db.routines:
                lines.append(f"- **{r.routine_type}** `{r.schema}.{r.name}`")

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Table sheet
    # ------------------------------------------------------------------

    def _render_table(self, table: TableInfo) -> str:
        tm = self._metrics.get(table.full_name)
        col_metrics = {cm.column_name: cm for cm in tm.column_metrics} if tm else {}
        has_metrics = bool(col_metrics)

        lines = [
            f"# `{table.schema}`.`{table.name}`",
            "",
            f"> **Type:** {table.table_type}  ",
            f"> **Schema:** `{table.schema}`  ",
        ]
        if table.row_count is not None:
            lines.append(f"> **Row count:** {table.row_count:,}")

        lines += ["", "---", "", "## Columns", ""]

        if has_metrics:
            lines += [
                "| # | Column | Type | Nullable | PK | Null % | Distinct | Min | Max | Top Values |",
                "|---|---|---|---|---|---|---|---|---|---|",
            ]
        else:
            lines += [
                "| # | Column | Type | Nullable | PK | Default |",
                "|---|---|---|---|---|---|",
            ]

        for i, col in enumerate(table.columns, 1):
            dtype = col.data_type + (f"({col.max_length})" if col.max_length else "")
            pk = "🔑" if col.is_primary_key else ""

            if has_metrics and col.name in col_metrics:
                cm = col_metrics[col.name]
                top = ", ".join(f"`{v}`" for v, _ in cm.top_values[:3]) or "—"
                lines.append(
                    f"| {i} | `{col.name}` | `{dtype}` | {_nullable(col.is_nullable)} | {pk}"
                    f" | {_pct(cm.null_rate)} | {cm.distinct_count:,}"
                    f" | {_v(cm.min_value)} | {_v(cm.max_value)} | {top} |"
                )
            else:
                lines.append(
                    f"| {i} | `{col.name}` | `{dtype}` | {_nullable(col.is_nullable)} | {pk}"
                    f" | {_v(col.default_value)} |"
                )

        # Primary Key
        if table.primary_key_columns:
            lines += [
                "",
                "## Primary Key",
                "",
                f"**Columns:** {', '.join(f'`{c}`' for c in table.primary_key_columns)}",
            ]

        # Foreign Keys
        if table.foreign_keys:
            lines += [
                "",
                "## Foreign Keys",
                "",
                "| Constraint | Column | References |",
                "|---|---|---|",
            ]
            for fk in table.foreign_keys:
                ref = f"`{fk.referenced_schema}`.`{fk.referenced_table}`.`{fk.referenced_column}`"
                lines.append(f"| `{fk.constraint_name}` | `{fk.column}` | {ref} |")

        # Indexes
        if table.indexes:
            lines += [
                "",
                "## Indexes",
                "",
                "| Name | Columns | Unique | PK |",
                "|---|---|---|---|",
            ]
            for idx in table.indexes:
                cols = ", ".join(f"`{c}`" for c in idx.columns)
                lines.append(
                    f"| `{idx.name}` | {cols}"
                    f" | {_nullable(idx.is_unique)} | {_nullable(idx.is_primary_key)} |"
                )

        # Numeric stats
        if has_metrics:
            numeric = [cm for cm in col_metrics.values() if cm.avg_value is not None]
            if numeric:
                lines += [
                    "",
                    "## Numeric Column Stats",
                    "",
                    "| Column | Avg | Min | Max |",
                    "|---|---|---|---|",
                ]
                for cm in numeric:
                    lines.append(
                        f"| `{cm.column_name}` | {_v(cm.avg_value)}"
                        f" | {_v(cm.min_value)} | {_v(cm.max_value)} |"
                    )

        return "\n".join(lines) + "\n"
