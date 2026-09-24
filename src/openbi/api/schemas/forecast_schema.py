from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ForecastPoint(BaseModel):
    forecast_month: date
    model_name: str
    yhat: float
    yhat_lower: float | None = None
    yhat_upper: float | None = None
    is_winner: bool
