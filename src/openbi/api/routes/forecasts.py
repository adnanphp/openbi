"""OpenBI — forecast endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import Connection

from openbi.api.cache import cache_get, cache_set
from openbi.api.dependencies import get_db
from openbi.api.schemas.forecast_schema import ForecastPoint

router = APIRouter(prefix="/forecasts", tags=["forecasts"])

TTL_FORECAST = 600


@router.get("/latest", response_model=list[ForecastPoint])
def latest(db: Connection = Depends(get_db)) -> list[ForecastPoint]:
    cached = cache_get("forecasts:latest")
    if cached is not None:
        return [ForecastPoint(**row) for row in cached]

    sql = text("""
        SELECT forecast_month, model_name, yhat, yhat_lower, yhat_upper, is_winner
        FROM warehouse.sales_forecast
        WHERE is_winner = TRUE
        ORDER BY forecast_month
    """)
    result = [ForecastPoint(**dict(r)) for r in db.execute(sql).mappings()]
    cache_set(
        "forecasts:latest",
        [r.model_dump() for r in result],
        ttl=TTL_FORECAST,
    )
    return result


@router.get("/models", response_model=list[ForecastPoint])
def all_models(db: Connection = Depends(get_db)) -> list[ForecastPoint]:
    cached = cache_get("forecasts:models")
    if cached is not None:
        return [ForecastPoint(**row) for row in cached]

    sql = text("""
        SELECT forecast_month, model_name, yhat, yhat_lower, yhat_upper, is_winner
        FROM warehouse.sales_forecast
        ORDER BY model_name, forecast_month
    """)
    result = [ForecastPoint(**dict(r)) for r in db.execute(sql).mappings()]
    cache_set(
        "forecasts:models",
        [r.model_dump() for r in result],
        ttl=TTL_FORECAST,
    )
    return result
