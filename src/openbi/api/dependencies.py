"""OpenBI — FastAPI shared dependencies."""

from __future__ import annotations

from typing import Iterator

from sqlalchemy.engine import Connection

from openbi.utils.db import get_engine


def get_db() -> Iterator[Connection]:
    """Yield a SQLAlchemy connection per request."""
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
