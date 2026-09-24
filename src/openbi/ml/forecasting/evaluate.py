"""OpenBI — train/validation split + model comparison."""

from __future__ import annotations

import numpy as np
import pandas as pd

from openbi.ml.forecasting.baseline import moving_average_forecast
from openbi.ml.forecasting.exponential_smoothing import ets_forecast
from openbi.ml.forecasting.xgboost_model import xgb_forecast


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def compare_models(
    series: pd.Series,
    holdout_months: int = 6,
) -> pd.DataFrame:
    """Fit each model on train, evaluate on last `holdout_months`."""
    train = series.iloc[:-holdout_months]
    test  = series.iloc[-holdout_months:]

    results = []

    # baseline
    try:
        pred = moving_average_forecast(train, horizon=holdout_months)["yhat"].values
        results.append({
            "model": "baseline_ma",
            "mape": mape(test.values, pred),
            "rmse": rmse(test.values, pred),
        })
    except Exception as e:  # noqa: BLE001
        print(f"  baseline failed: {e}")

    # ETS
    try:
        pred = ets_forecast(train, horizon=holdout_months)["yhat"].values
        results.append({
            "model": "ets",
            "mape": mape(test.values, pred),
            "rmse": rmse(test.values, pred),
        })
    except Exception as e:  # noqa: BLE001
        print(f"  ETS failed: {e}")

    # XGBoost
    try:
        pred = xgb_forecast(train, horizon=holdout_months)["yhat"].values
        results.append({
            "model": "xgboost",
            "mape": mape(test.values, pred),
            "rmse": rmse(test.values, pred),
        })
    except Exception as e:  # noqa: BLE001
        print(f"  XGBoost failed: {e}")

    df = pd.DataFrame(results).sort_values("mape").reset_index(drop=True)
    return df
