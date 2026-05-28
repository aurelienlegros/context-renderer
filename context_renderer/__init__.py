"""
context-renderer
~~~~~~~~~~~~~~~~
Generate structured Markdown context sheets from MSSQL databases.

Basic usage::

    from context_renderer import MSSQLConnector, DatabaseInspector, DataMetrics, ContextSheetRenderer

    connector = MSSQLConnector(host="...", database="...", username="...", password="...")
    engine    = connector.get_engine()
    schema    = DatabaseInspector(engine).inspect()
    metrics   = DataMetrics(engine).compute_all(schema.tables)
    ContextSheetRenderer(schema, metrics).save("./output")
"""

from .connector import MSSQLConnector
from .inspector import DatabaseInspector
from .metrics import DataMetrics
from .renderer import ContextSheetRenderer

__version__ = "0.1.0"
__all__ = [
    "MSSQLConnector",
    "DatabaseInspector",
    "DataMetrics",
    "ContextSheetRenderer",
]
