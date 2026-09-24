"""OpenBI — Holt-Winters Exponential Smoothing forecast."""

from __future__ import annotations

import warnings

import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def ets_forecast(
    series: pd.Series,
    horizon: int = 6,
    seasonal_periods: int = 12,
) -> pd.DataFrame:
    """Fit Holt-Winters and forecast `horizon` periods ahead."""
    series = series.asfreq("MS")

    # Need at least 2 full seasonal cycles for a seasonal model
    if len(series) < 2 * seasonal_periods:
        seasonal = None
        seasonal_periods = None
    else:
        seasonal = "add"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = ExponentialSmoothing(
            series,
            trend="add",
            seasonal=seasonal,
            seasonal_periods=seasonal_periods,
            initialization_method="estimated",
        ).fit(optimized=True)

    forecast = model.forecast(horizon)

    # Approximate prediction intervals via residual std
    resid_std = float(model.resid.std())
    return pd.DataFrame({
        "yhat":       forecast.values,
        "yhat_lower": forecast.values - 1.96 * resid_std,
        "yhat_upper": forecast.values + 1.96 * resid_std,
    }, index=forecast.index)
