"""
connector.py
~~~~~~~~~~~~
MSSQL connection management via SQLAlchemy + pyodbc.

Supports reading credentials from environment variables via a classmethod,
which pairs naturally with the .env / docker-compose workflow.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class MSSQLConnector:
    """
    Manages a connection to a Microsoft SQL Server database.

    Direct instantiation::

        conn = MSSQLConnector(
            host="localhost",
            database="MyDB",
            username="sa",
            password="secret",
        )

    From environment variables (.env / docker-compose env_file)::

        conn = MSSQLConnector.from_env()
        # reads MSSQL_HOST, MSSQL_DATABASE, MSSQL_USERNAME, MSSQL_PASSWORD
        # optional: MSSQL_PORT, MSSQL_TRUST_SERVER_CERTIFICATE
    """

    def __init__(
        self,
        host: str,
        database: str,
        username: str,
        password: str,
        port: int = 1433,
        driver: str = "ODBC Driver 18 for SQL Server",
        trust_server_certificate: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.driver = driver
        self.trust_server_certificate = trust_server_certificate
        self._engine: Engine | None = None

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "MSSQLConnector":
        """Build a connector from environment variables."""
        return cls(
            host=os.environ["MSSQL_HOST"],
            database=os.environ["MSSQL_DATABASE"],
            username=os.environ["MSSQL_USERNAME"],
            password=os.environ["MSSQL_PASSWORD"],
            port=int(os.getenv("MSSQL_PORT", "1433")),
            trust_server_certificate=os.getenv(
                "MSSQL_TRUST_SERVER_CERTIFICATE", "yes"
            ).lower() == "yes",
        )

    # ------------------------------------------------------------------
    # Engine
    # ------------------------------------------------------------------

    def get_engine(self) -> Engine:
        """Return a cached SQLAlchemy engine (lazy init)."""
        if self._engine is None:
            self._engine = self._build_engine()
        return self._engine

    def _build_engine(self) -> Engine:
        trust = "yes" if self.trust_server_certificate else "no"
        driver_str = self.driver.replace(" ", "+")
        url = (
            f"mssql+pyodbc://{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
            f"?driver={driver_str}"
            f"&TrustServerCertificate={trust}"
        )
        return create_engine(url, fast_executemany=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def test_connection(self) -> bool:
        """Return True if the connection is successful, False otherwise."""
        try:
            with self.get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            print(f"[MSSQLConnector] Connection failed: {exc}")
            return False

    def close(self) -> None:
        """Dispose of the engine and release all connections."""
        if self._engine:
            self._engine.dispose()
            self._engine = None

    def __repr__(self) -> str:
        return (
            f"MSSQLConnector(host={self.host!r}, port={self.port}, "
            f"database={self.database!r}, username={self.username!r})"
        )
