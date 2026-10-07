"""OpenBI — sales KPI endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import Connection

from openbi.api.cache import cache_get, cache_set
from openbi.api.dependencies import get_db
from openbi.api.schemas.sales_schema import (
    CategoryRevenue,
    ExecutiveKPI,
    MonthlyRevenue,
)

router = APIRouter(prefix="/kpis", tags=["sales"])

TTL_EXECUTIVE = 300
TTL_MONTHLY = 300
TTL_CATEGORY = 300


@router.get("/executive", response_model=ExecutiveKPI)
def executive(db: Connection = Depends(get_db)) -> ExecutiveKPI:
    cached = cache_get("kpis:executive")
    if cached is not None:
        return ExecutiveKPI(**cached)

    sql = text("""
        SELECT
            SUM(sales)                    AS total_revenue,
            SUM(profit)                   AS total_profit,
            COUNT(DISTINCT order_id)      AS total_orders,
            SUM(sales) / COUNT(DISTINCT order_id) AS avg_order_value,
            100.0 * SUM(profit) / NULLIF(SUM(sales), 0) AS profit_margin_pct
        FROM warehouse.fact_sales
    """)
    row = db.execute(sql).mappings().one()
    result = ExecutiveKPI(
        total_revenue=float(row["total_revenue"]),
        total_profit=float(row["total_profit"]),
        total_orders=int(row["total_orders"]),
        avg_order_value=float(row["avg_order_value"]),
        profit_margin_pct=round(float(row["profit_margin_pct"]), 2),
    )
    cache_set("kpis:executive", result.model_dump(), ttl=TTL_EXECUTIVE)
    return result


@router.get("/monthly-revenue", response_model=list[MonthlyRevenue])
def monthly_revenue(db: Connection = Depends(get_db)) -> list[MonthlyRevenue]:
    cached = cache_get("kpis:monthly_revenue")
    if cached is not None:
        return [MonthlyRevenue(**row) for row in cached]

    sql = text("""
        SELECT year, month, month_name, revenue, profit, orders
        FROM warehouse.v_monthly_revenue
        ORDER BY year, month
    """)
    result = [MonthlyRevenue(**dict(r)) for r in db.execute(sql).mappings()]
    cache_set(
        "kpis:monthly_revenue",
        [r.model_dump() for r in result],
        ttl=TTL_MONTHLY,
    )
    return result


@router.get("/by-category", response_model=list[CategoryRevenue])
def by_category(db: Connection = Depends(get_db)) -> list[CategoryRevenue]:
    cached = cache_get("kpis:by_category")
    if cached is not None:
        return [CategoryRevenue(**row) for row in cached]

    sql = text("""
        SELECT category, SUM(revenue) AS revenue, SUM(profit) AS profit, SUM(units) AS units
        FROM warehouse.v_revenue_by_category
        GROUP BY category
        ORDER BY revenue DESC
    """)
    result = [CategoryRevenue(**dict(r)) for r in db.execute(sql).mappings()]
    cache_set(
        "kpis:by_category",
        [r.model_dump() for r in result],
        ttl=TTL_CATEGORY,
    )
    return result
