"""Integration tests for the FastAPI layer.

Requires a running warehouse (Postgres with loaded data).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openbi.api.main import app
from openbi.utils.db import ping

pytestmark = pytest.mark.skipif(not ping(), reason="DB not reachable")

client = TestClient(app)


# --------------------------------------------------------------- meta
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "OK"


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "OpenBI API"


# --------------------------------------------------------------- kpis
def test_executive_kpi():
    r = client.get("/kpis/executive")
    assert r.status_code == 200
    body = r.json()

    # exact totals from source data
    assert abs(body["total_revenue"] - 2_297_200.86) < 0.01
    assert abs(body["total_profit"]  -   286_397.02) < 0.01
    assert body["total_orders"] == 5009
    assert 0 < body["profit_margin_pct"] < 100


def test_monthly_revenue_returns_48_rows():
    r = client.get("/kpis/monthly-revenue")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 48            # 4 years × 12 months
    assert rows[0]["year"] == 2014
    assert rows[0]["month"] == 1


def test_category_revenue_sorted_desc():
    r = client.get("/kpis/by-category")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 3             # Furniture, Office Supplies, Technology
    revenues = [row["revenue"] for row in rows]
    assert revenues == sorted(revenues, reverse=True)


# --------------------------------------------------------------- customers
def test_segments_endpoint():
    r = client.get("/customers/segments")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 7             # Champions, Loyal, At Risk, etc.

    labels = {row["cluster_label"] for row in rows}
    assert "Champions" in labels
    assert "At Risk" in labels
    assert "Lost" in labels

    # Champions must have lowest recency of all segments
    champions = next(row for row in rows if row["cluster_label"] == "Champions")
    lost = next(row for row in rows if row["cluster_label"] == "Lost")
    assert champions["avg_recency_days"] < lost["avg_recency_days"]


# --------------------------------------------------------------- forecasts
def test_forecast_latest_returns_6_months():
    r = client.get("/forecasts/latest")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 6             # 6-month horizon
    assert all(row["is_winner"] for row in rows)
    # winner should be ETS based on our model comparison
    assert rows[0]["model_name"] == "ets"


def test_forecast_all_models_returns_18():
    r = client.get("/forecasts/models")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 18            # 6 months × 3 models
    models = {row["model_name"] for row in rows}
    assert models == {"ets", "xgboost", "baseline_ma"}
