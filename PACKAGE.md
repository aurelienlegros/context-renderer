# context-renderer

> Generate structured Markdown context sheets from your MSSQL databases — in one command.

[![PyPI](https://img.shields.io/pypi/v/context-renderer)](https://pypi.org/project/context-renderer/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/aurelienlegros/context-renderer/blob/master/LICENSE)

`context-renderer` connects to a Microsoft SQL Server database, inspects its full structure, computes data metrics, and produces clean **Markdown context sheets** — one overview + one detailed file per table.

Perfect for onboarding, documentation, LLM context injection, or just understanding an unfamiliar database.

---

## Installation

```bash
pip install context-renderer
```

> **Prerequisite:** [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) must be installed on the host machine.

---

## Usage

```python
from context_renderer import MSSQLConnector, DatabaseInspector, DataMetrics, ContextSheetRenderer

# 1. Connect
connector = MSSQLConnector(host="your-server", database="your-db", username="sa", password="...")
engine = connector.get_engine()

# 2. Inspect schema
schema = DatabaseInspector(engine).inspect()

# 3. Compute data metrics (optional — skip for speed)
metrics = DataMetrics(engine).compute_all(schema.tables)

# 4. Save context sheets
ContextSheetRenderer(schema, metrics).save("./output")
```

### Output structure

```
output/your-db/
├── 00_database_overview.md     ← Summary, table list, FK relation map, routines
├── dbo__Users.md               ← Columns, PKs, FKs, indexes, null %, cardinality, top values
├── dbo__Orders.md
└── ...
```

---

## What the sheets look like

### `00_database_overview.md`

```markdown
# Database Overview — `MyDatabase`

## Summary
| Property | Value          |
|----------|----------------|
| Schemas  | `dbo`, `audit` |
| Tables   | 12             |
| Views    | 3              |

## Foreign Key Relations
- `dbo.Orders.user_id` → `dbo.Users.id`
- `dbo.OrderItems.order_id` → `dbo.Orders.id`
```

### `dbo__Orders.md`

```markdown
# `dbo`.`Orders`
> Row count: 1,482,309

## Columns
| # | Column   | Type          | Nullable | PK | Null % | Distinct | Top Values        |
|---|----------|---------------|----------|----|--------|----------|-------------------|
| 1 | `id`     | `int`         | ✗        | 🔑 | 0.0%   | 1482309  | —                 |
| 2 | `status` | `varchar(20)` | ✗        |    | 0.0%   | 4        | `pending`, `paid` |
| 3 | `amount` | `decimal`     | ✓        |    | 2.1%   | 18402    | —                 |
```

---

## Full project & Jupyter notebook

For a Docker-based Jupyter workflow (no local ODBC setup required), see the [project repository](https://github.com/aurelienlegros/context-renderer).

---

## License

MIT — see [LICENSE](https://github.com/aurelienlegros/context-renderer/blob/master/LICENSE).
