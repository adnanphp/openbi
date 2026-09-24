"""Integration tests — require running Postgres with loaded warehouse."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from openbi.utils.db import get_engine, ping


pytestmark = pytest.mark.skipif(not ping(), reason="DB not reachable")


def test_fact_sales_row_count():
    with get_engine().connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM warehouse.fact_sales")).scalar()
    assert n == 9994, f"Expected 9,994 rows, got {n}"


def test_revenue_total():
    with get_engine().connect() as conn:
        rev = conn.execute(
            text("SELECT SUM(sales) FROM warehouse.fact_sales")
        ).scalar()
    assert abs(float(rev) - 2297200.86) < 0.01


def test_profit_total():
    with get_engine().connect() as conn:
        profit = conn.execute(
            text("SELECT SUM(profit) FROM warehouse.fact_sales")
        ).scalar()
    assert abs(float(profit) - 286397.02) < 0.01


def test_dimensions_populated():
    with get_engine().connect() as conn:
        customers = conn.execute(
            text("SELECT COUNT(*) FROM warehouse.dim_customer")
        ).scalar()
        products = conn.execute(
            text("SELECT COUNT(*) FROM warehouse.dim_product")
        ).scalar()
    assert customers == 793
    assert products == 1862


def test_ml_tables_populated():
    with get_engine().connect() as conn:
        segments = conn.execute(
            text("SELECT COUNT(*) FROM warehouse.customer_segments")
        ).scalar()
        forecasts = conn.execute(
            text("SELECT COUNT(*) FROM warehouse.sales_forecast")
        ).scalar()
    assert segments == 793
    assert forecasts == 18
