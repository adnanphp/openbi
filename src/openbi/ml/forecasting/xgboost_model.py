"""OpenBI — XGBoost forecasting with lag + calendar features."""

from __future__ import annotations

import numpy as np
import pandas as pd
from xgboost import XGBRegressor


def _make_features(series: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"y": series.values}, index=series.index)
    # lags
    for lag in (1, 2, 3, 12):
        df[f"lag_{lag}"] = df["y"].shift(lag)
    # rolling
    df["roll_3"]  = df["y"].shift(1).rolling(3).mean()
    df["roll_6"]  = df["y"].shift(1).rolling(6).mean()
    df["roll_12"] = df["y"].shift(1).rolling(12).mean()
    # calendar
    df["month"]   = df.index.month
    df["quarter"] = df.index.quarter
    df["year"]    = df.index.year
    return df.dropna()


def xgb_forecast(
    series: pd.Series,
    horizon: int = 6,
) -> pd.DataFrame:
    """Fit XGBoost on lag features and recursively predict `horizon` months."""
    series = series.asfreq("MS")
    feat = _make_features(series)

    if len(feat) < 12:
        raise ValueError(f"Not enough history for XGBoost: {len(feat)} rows")

    X = feat.drop(columns=["y"])
    y = feat["y"]

    model = XGBRegressor(
        n_estimators=300,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        objective="reg:squarederror",
    )
    model.fit(X, y)

    # ---- recursive forecast ----
    history = series.copy()
    preds: list[float] = []
    idxs: list[pd.Timestamp] = []

    for _ in range(horizon):
        next_idx = history.index[-1] + pd.DateOffset(months=1)
        row = _make_features(history).iloc[-1:].drop(columns=["y"])
        yhat = float(model.predict(row)[0])

        preds.append(yhat)
        idxs.append(next_idx)

        # extend history with the prediction
        history = pd.concat([history, pd.Series([yhat], index=[next_idx])])

    resid_std = float((y - model.predict(X)).std())
    return pd.DataFrame({
        "yhat":       preds,
        "yhat_lower": np.array(preds) - 1.96 * resid_std,
        "yhat_upper": np.array(preds) + 1.96 * resid_std,
    }, index=pd.DatetimeIndex(idxs))
