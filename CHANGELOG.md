# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.1.3] — 2026-05-28

### Fixed
- PyPI publish failure on duplicate version: version is now derived dynamically from the git tag via `hatch-vcs` (`dynamic = ["version"]`) — no more manual update of `pyproject.toml`

### Changed
- `pyproject.toml`: replaced static `version` with `dynamic = ["version"]`; added `hatch-vcs` to build requirements
- `publish.yml`: added `fetch-depth: 0` to checkout so `hatch-vcs` can read the full tag history

## [0.1.2] — 2026-05-28

### Added
- GitHub Actions workflow for automated PyPI publish on `v*.*.*` tags via OIDC trusted publishing (no token required)
- `PACKAGE.md` as dedicated PyPI long description (install, API usage, output examples)

### Changed
- `pyproject.toml`: `readme` points to `PACKAGE.md`; added `[project.urls]`; added `notebooks` optional dependency group; sdist manifest restricted to package sources
- Dockerfile: replaced `pip` + `requirements.txt` with `uv pip install -e "[notebooks]"`

## [0.1.1] — 2026-05-28

### Fixed
- `pyproject.toml`: corrected misplaced `[project.urls]` section that caused a build error (`dependencies` interpreted as a URL key)

## [0.1.0] — 2026-05-28

### Added
- `MSSQLConnector` — SQLAlchemy + pyodbc connection with `.from_env()` classmethod
- `DatabaseInspector` — extracts schemas, tables, views, columns, PKs, FKs, indexes, row counts, stored procedures and functions
- `DataMetrics` — per-column null rates, distinct counts, cardinality, min/max/avg, top N values
- `ContextSheetRenderer` — generates `00_database_overview.md` + one `.md` per table/view
- Docker + Jupyter setup with one-command start
- Example notebook `01_generate_context_sheets.ipynb`
