"""OpenBI — forecast endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import Connection

from openbi.api.dependencies import get_db
from openbi.api.schemas.forecast_schema import ForecastPoint

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.get("/latest", response_model=list[ForecastPoint])
def latest(db: Connection = Depends(get_db)) -> list[ForecastPoint]:
    """Winning model's forecast for the next horizon."""
    sql = text("""
        SELECT forecast_month, model_name, yhat, yhat_lower, yhat_upper, is_winner
        FROM warehouse.sales_forecast
        WHERE is_winner = TRUE
        ORDER BY forecast_month
    """)
    return [ForecastPoint(**dict(r)) for r in db.execute(sql).mappings()]


@router.get("/models", response_model=list[ForecastPoint])
def all_models(db: Connection = Depends(get_db)) -> list[ForecastPoint]:
    """All candidate models' forecasts (for comparison)."""
    sql = text("""
        SELECT forecast_month, model_name, yhat, yhat_lower, yhat_upper, is_winner
        FROM warehouse.sales_forecast
        ORDER BY model_name, forecast_month
    """)
    return [ForecastPoint(**dict(r)) for r in db.execute(sql).mappings()]
