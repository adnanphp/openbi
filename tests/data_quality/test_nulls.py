"""Data quality checks — critical columns must not be null."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from openbi.utils.db import get_engine, ping


pytestmark = pytest.mark.skipif(not ping(), reason="DB not reachable")


@pytest.mark.parametrize("col", ["order_id", "customer_key", "product_key",
                                 "order_date_key", "sales", "quantity"])
def test_fact_sales_critical_not_null(col: str):
    with get_engine().connect() as conn:
        n = conn.execute(
            text(f"SELECT COUNT(*) FROM warehouse.fact_sales WHERE {col} IS NULL")
        ).scalar()
    assert n == 0, f"{col} has {n} nulls"


def test_dim_customer_ids_unique():
    with get_engine().connect() as conn:
        dupes = conn.execute(text("""
            SELECT customer_id, COUNT(*)
            FROM warehouse.dim_customer
            GROUP BY customer_id HAVING COUNT(*) > 1
        """)).fetchall()
    assert len(dupes) == 0


def test_no_future_dates():
    with get_engine().connect() as conn:
        future = conn.execute(text("""
            SELECT COUNT(*)
            FROM warehouse.fact_sales f
            JOIN warehouse.dim_date d ON d.date_key = f.order_date_key
            WHERE d.full_date > CURRENT_DATE
        """)).scalar()
    assert future == 0
