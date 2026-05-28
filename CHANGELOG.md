# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.1.0] — 2026-05-28

### Added
- `MSSQLConnector` — SQLAlchemy + pyodbc connection with `.from_env()` classmethod
- `DatabaseInspector` — extracts schemas, tables, views, columns, PKs, FKs, indexes, row counts, stored procedures and functions
- `DataMetrics` — per-column null rates, distinct counts, cardinality, min/max/avg, top N values
- `ContextSheetRenderer` — generates `00_database_overview.md` + one `.md` per table/view
- Docker + Jupyter setup with one-command start
- Example notebook `01_generate_context_sheets.ipynb`
