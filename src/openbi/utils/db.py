"""OpenBI — database helpers."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from openbi.config.settings import settings

_engine: Engine | None = None


def get_engine() -> Engine:
    """Singleton SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
    return _engine


@contextmanager
def get_conn() -> Iterator:
    """Context manager yielding a connection with auto-commit."""
    engine = get_engine()
    with engine.begin() as conn:
        yield conn


def execute_sql_file(path: str | Path) -> None:
    """Run a multi-statement SQL file."""
    path = Path(path)
    sql_text = path.read_text(encoding="utf-8")
    # split on ';' at end of line — safe enough for our controlled SQL files
    with get_conn() as conn:
        conn.execute(text(sql_text))


def execute_sql_string(sql: str) -> None:
    with get_conn() as conn:
        conn.execute(text(sql))


def read_sql(sql: str, params: dict | None = None) -> pd.DataFrame:
    return pd.read_sql(text(sql), get_engine(), params=params or {})


def load_dataframe(
    df: pd.DataFrame,
    table: str,
    schema: str,
    if_exists: str = "replace",
    chunksize: int = 1000,
) -> None:
    """Push a DataFrame to Postgres."""
    df.to_sql(
        name=table,
        con=get_engine(),
        schema=schema,
        if_exists=if_exists,
        index=False,
        method="multi",
        chunksize=chunksize,
    )


def ping() -> bool:
    try:
        with get_conn() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  DB ping failed: {exc}")
        return False
