# context-renderer

> **Generate structured Markdown context sheets from your MSSQL databases — in one command.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker)](docker-compose.yml)

`context-renderer` connects to a Microsoft SQL Server database, inspects its full structure, computes data metrics, and produces clean **Markdown context sheets** — one overview + one detailed file per table.

Perfect for onboarding, documentation, LLM context injection, or just understanding an unfamiliar database.

---

## What it generates

```
output/MyDatabase/
├── 00_database_overview.md     ← Summary, table list, FK relation map, routines
├── dbo__Users.md               ← Columns, PKs, FKs, indexes, null %, cardinality, top values
├── dbo__Orders.md
└── ...
```

### Example — `00_database_overview.md`

```markdown
# Database Overview — `MyDatabase`

## Summary
| Property  | Value          |
|-----------|----------------|
| Schemas   | `dbo`, `audit` |
| Tables    | 12             |
| Views     | 3              |

## Foreign Key Relations
- `dbo.Orders.user_id` → `dbo.Users.id`
- `dbo.OrderItems.order_id` → `dbo.Orders.id`
```

### Example — `dbo__Orders.md`

```markdown
# `dbo`.`Orders`
> Row count: 1,482,309

## Columns
| # | Column     | Type          | Nullable | PK | Null % | Distinct | Top Values          |
|---|------------|---------------|----------|----|--------|----------|---------------------|
| 1 | `id`       | `int`         | ✗        | 🔑 | 0.0%   | 1482309  | —                   |
| 2 | `status`   | `varchar(20)` | ✗        |    | 0.0%   | 4        | `pending`, `paid`   |
| 3 | `amount`   | `decimal`     | ✓        |    | 2.1%   | 18402    | —                   |
```

---

## Quickstart

### Requirements
- [Docker](https://www.docker.com/) & Docker Compose
- A reachable SQL Server instance (2016+)

### 1. Clone

```bash
git clone https://github.com/your-username/context-renderer.git
cd context-renderer
```

### 2. Start Jupyter

```bash
docker compose up --build
```

Open [http://localhost:8888](http://localhost:8888)

### 3. Run the notebook

Open `notebooks/01_generate_context_sheets.ipynb`, fill in your connection:

```python
connector = MSSQLConnector(
    host="your-server",
    database="your-database",
    username="sa",
    password="your-password",
)
```

Run all cells → sheets are saved to `notebooks/output/{database}/`.

---

## Package API

You can also use the `context_renderer` package directly:

```python
from context_renderer import MSSQLConnector, DatabaseInspector, DataMetrics, ContextSheetRenderer

# 1. Connect
connector = MSSQLConnector(host="...", database="...", username="...", password="...")
engine = connector.get_engine()

# 2. Inspect schema
schema = DatabaseInspector(engine).inspect()

# 3. Compute data metrics (optional — skip for speed)
metrics = DataMetrics(engine).compute_all(schema.tables)

# 4. Save context sheets
ContextSheetRenderer(schema, metrics).save("./output")
```

---

## Project Structure

```
context-renderer/
├── docker-compose.yml
├── docker/
│   ├── Dockerfile
│   └── requirements.txt
├── notebooks/
│   ├── 01_generate_context_sheets.ipynb
│   └── output/                       ← generated sheets (git-ignored)
├── context_renderer/                 ← Python package
│   ├── __init__.py
│   ├── connector.py                  ← MSSQL connection (SQLAlchemy + pyodbc)
│   ├── inspector.py                  ← Schema metadata (tables, columns, PKs, FKs, indexes)
│   ├── metrics.py                    ← Data statistics (null rate, cardinality, top values)
│   └── renderer.py                   ← Markdown context sheet renderer
├── pyproject.toml
├── .gitignore
└── LICENSE
```

---

## Roadmap

- [ ] PostgreSQL & MySQL connectors
- [ ] API source support (REST → context sheet)
- [ ] LLM-powered natural language table summaries
- [ ] CLI interface (`context-renderer run --host ... --db ...`)
- [ ] HTML output format

---

## License

MIT — see [LICENSE](LICENSE).
