"""OpenBI — naive / moving-average baseline forecast."""

from __future__ import annotations

import numpy as np
import pandas as pd


def moving_average_forecast(
    series: pd.Series,
    horizon: int = 6,
    window: int = 3,
) -> pd.DataFrame:
    """Predict next `horizon` months as the mean of the last `window` values."""
    if len(series) < window:
        raise ValueError(f"Need at least {window} observations, got {len(series)}")

    last_avg = series.tail(window).mean()
    future_idx = pd.date_range(
        series.index[-1] + pd.DateOffset(months=1),
        periods=horizon,
        freq="MS",
    )
    return pd.DataFrame({"yhat": [last_avg] * horizon}, index=future_idx)


def naive_forecast(series: pd.Series, horizon: int = 6) -> pd.DataFrame:
    """Predict next `horizon` months as the last observed value."""
    last = series.iloc[-1]
    future_idx = pd.date_range(
        series.index[-1] + pd.DateOffset(months=1),
        periods=horizon,
        freq="MS",
    )
    return pd.DataFrame({"yhat": [last] * horizon}, index=future_idx)
