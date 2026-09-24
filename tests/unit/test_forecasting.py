"""Validate forecasting model outputs."""

from __future__ import annotations

import numpy as np
import pandas as pd

from openbi.ml.forecasting.baseline import moving_average_forecast
from openbi.ml.forecasting.evaluate import mape, rmse


def test_moving_average_returns_correct_horizon():
    series = pd.Series(
        np.arange(24, dtype=float),
        index=pd.date_range("2020-01-01", periods=24, freq="MS"),
    )
    fc = moving_average_forecast(series, horizon=6, window=3)
    assert len(fc) == 6
    assert "yhat" in fc.columns


def test_mape_zero_on_perfect_prediction():
    y = np.array([1.0, 2.0, 3.0])
    assert mape(y, y) == 0.0


def test_rmse_zero_on_perfect_prediction():
    y = np.array([1.0, 2.0, 3.0])
    assert rmse(y, y) == 0.0


def test_mape_positive_when_differs():
    y_true = np.array([100.0, 200.0])
    y_pred = np.array([110.0, 180.0])
    assert mape(y_true, y_pred) > 0
