"""OpenBI Phase D — Sales forecasting at v2 scale.

Forecasting on 96 monthly points is done on the driver (statsmodels ETS,
XGBoost). Spark's role is to aggregate 1M rows of fact_sales into the
monthly series fast and distribute the aggregation.

Models:
  - baseline_ma  : 3-month moving average
  - ets          : Holt-Winters Exponential Smoothing
  - xgboost      : gradient boosting on lag features

Winner selected by holdout MAPE.

Run:
    ./spark/run_job.sh jobs/ml_forecast.py
"""

from __future__ import annotations

import argparse
import time
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from xgboost import XGBRegressor

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


SILVER_ROOT = "/opt/openbi/data/silver"
GOLD_ROOT = "/opt/openbi/data/gold"

HORIZON = 6
HOLDOUT = 6


def build_spark(app_name: str = "openbi-ml-forecast") -> SparkSession:
    return (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )


def _section(title: str) -> None:
    print(f"\n{'─' * 70}\n▶ {title}\n{'─' * 70}")


# ============================================================ monthly series
def load_monthly_series(spark: SparkSession, fact_path: str, dim_date_path: str) -> pd.Series:
    fact = spark.read.format("delta").load(fact_path).drop("year")
    dim_date = spark.read.format("delta").load(dim_date_path)

    monthly = (
        fact.join(dim_date, fact.order_date_key == dim_date.date_key, "inner")
        .groupBy("year", "month")
        .agg(F.sum("sales").alias("revenue"))
        .orderBy("year", "month")
        .toPandas()
    )
    monthly["month"] = pd.to_datetime(dict(year=monthly["year"], month=monthly["month"], day=1))
    return monthly.set_index("month")["revenue"].astype(float).sort_index()


# ================================================================= metrics
def mape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def rmse(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


# ================================================================= models
def baseline_ma(series: pd.Series, horizon: int, window: int = 3) -> pd.DataFrame:
    val = series.tail(window).mean()
    idx = pd.date_range(series.index[-1] + pd.DateOffset(months=1), periods=horizon, freq="MS")
    return pd.DataFrame({"yhat": [val] * horizon}, index=idx)


def ets_forecast(series: pd.Series, horizon: int) -> pd.DataFrame:
    series = series.asfreq("MS")
    seasonal = "add" if len(series) >= 24 else None
    sp = 12 if seasonal else None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = ExponentialSmoothing(
            series, trend="add", seasonal=seasonal, seasonal_periods=sp,
            initialization_method="estimated",
        ).fit(optimized=True)
    fc = model.forecast(horizon)
    resid_std = float(model.resid.std())
    return pd.DataFrame({
        "yhat": fc.values,
        "yhat_lower": fc.values - 1.96 * resid_std,
        "yhat_upper": fc.values + 1.96 * resid_std,
    }, index=fc.index)


def _make_features(series: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"y": series.values}, index=series.index)
    for lag in (1, 2, 3, 12):
        df[f"lag_{lag}"] = df["y"].shift(lag)
    df["roll_3"] = df["y"].shift(1).rolling(3).mean()
    df["roll_6"] = df["y"].shift(1).rolling(6).mean()
    df["roll_12"] = df["y"].shift(1).rolling(12).mean()
    df["month"] = df.index.month
    df["quarter"] = df.index.quarter
    df["year"] = df.index.year
    return df.dropna()


def xgb_forecast(series: pd.Series, horizon: int) -> pd.DataFrame:
    series = series.asfreq("MS")
    feat = _make_features(series)
    if len(feat) < 12:
        raise ValueError(f"not enough history for XGBoost: {len(feat)} rows")

    X, y = feat.drop(columns=["y"]), feat["y"]
    model = XGBRegressor(
        n_estimators=300, max_depth=3, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.9, random_state=42,
        objective="reg:squarederror",
    ).fit(X, y)

    history = series.copy()
    preds, idxs = [], []
    for _ in range(horizon):
        nxt = history.index[-1] + pd.DateOffset(months=1)
        row = _make_features(history).iloc[-1:].drop(columns=["y"])
        yhat = max(0.0, float(model.predict(row)[0]))   # sales can't be negative
        preds.append(yhat)
        idxs.append(nxt)
        history = pd.concat([history, pd.Series([yhat], index=[nxt])])

    resid_std = float((y - model.predict(X)).std())
    return pd.DataFrame({
        "yhat": preds,
        "yhat_lower": np.array(preds) - 1.96 * resid_std,
        "yhat_upper": np.array(preds) + 1.96 * resid_std,
    }, index=pd.DatetimeIndex(idxs))


# ============================================================== orchestr
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--silver-root", default=SILVER_ROOT)
    ap.add_argument("--gold-root", default=GOLD_ROOT)
    args = ap.parse_args()

    print("=" * 70)
    print("  OpenBI — Sales Forecasting (v2 scale)")
    print("=" * 70)

    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    t0 = time.time()

    _section("Load monthly series from Silver")
    series = load_monthly_series(
        spark,
        f"{args.silver_root}/fact_sales",
        f"{args.silver_root}/dim_date",
    )
    print(f"  months: {len(series)}  ({series.index.min().date()} → {series.index.max().date()})")

    _section(f"Compare models on last {HOLDOUT} months (holdout)")
    train, test = series.iloc[:-HOLDOUT], series.iloc[-HOLDOUT:]

    results = []
    for name, fn in [
        ("baseline_ma", lambda s, h: baseline_ma(s, h)),
        ("ets",         lambda s, h: ets_forecast(s, h)),
        ("xgboost",     lambda s, h: xgb_forecast(s, h)),
    ]:
        try:
            fc = fn(train, HOLDOUT)["yhat"].values
            results.append({"model": name, "mape": mape(test.values, fc), "rmse": rmse(test.values, fc)})
        except Exception as e:
            print(f"  {name}: FAILED ({e})")

    comparison = pd.DataFrame(results).sort_values("mape").reset_index(drop=True)
    print(comparison.to_string(index=False))

    winner = comparison.iloc[0]["model"]
    print(f"\n  ✓ winner: {winner}  (MAPE {comparison.iloc[0]['mape']:.2f}%)")

    _section("Refit winner on full series, forecast next 6 months")
    if winner == "baseline_ma":
        final = baseline_ma(series, HORIZON)
    elif winner == "ets":
        final = ets_forecast(series, HORIZON)
    else:
        final = xgb_forecast(series, HORIZON)
    print(final.to_string())

    _section("Build full forecast table (all 3 models for comparison)")
    all_rows = []
    for name, fn in [
        ("baseline_ma", baseline_ma),
        ("ets",         ets_forecast),
        ("xgboost",     xgb_forecast),
    ]:
        try:
            fc = fn(series, HORIZON).reset_index().rename(columns={"index": "forecast_month"})
        except Exception as e:
            print(f"  skip {name}: {e}")
            continue
        fc["forecast_month"] = pd.to_datetime(fc["forecast_month"]).dt.date
        fc["model_name"] = name
        fc["is_winner"] = name == winner
        all_rows.append(fc)

    out = pd.concat(all_rows, ignore_index=True)
    if "yhat_lower" not in out.columns:
        out["yhat_lower"] = None
    if "yhat_upper" not in out.columns:
        out["yhat_upper"] = None
    out = out[["forecast_month", "model_name", "yhat", "yhat_lower", "yhat_upper", "is_winner"]]
    out["yhat"] = out["yhat"].round(2)
    out["yhat_lower"] = out["yhat_lower"].round(2)
    out["yhat_upper"] = out["yhat_upper"].round(2)

    out_spark = spark.createDataFrame(out)
    (out_spark.write
        .format("delta")
        .mode("overwrite")
        .save(f"{args.gold_root}/sales_forecast"))
    print(f"  ✓ wrote {out_spark.count():,} rows to data/gold/sales_forecast/")

    print(f"\n  elapsed: {time.time() - t0:.1f}s")
    spark.stop()
    print("\n✓ Forecasting complete")


if __name__ == "__main__":
    main()
