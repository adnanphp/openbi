from __future__ import annotations

from pydantic import BaseModel


class MonthlyRevenue(BaseModel):
    year: int
    month: int
    month_name: str
    revenue: float
    profit: float
    orders: int


class ExecutiveKPI(BaseModel):
    total_revenue: float
    total_profit: float
    total_orders: int
    avg_order_value: float
    profit_margin_pct: float


class CategoryRevenue(BaseModel):
    category: str
    revenue: float
    profit: float
    units: int
