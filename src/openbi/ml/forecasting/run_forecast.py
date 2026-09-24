"""OpenBI — orchestrate all forecast models and persist to warehouse."""

from __future__ import annotations

import pandas as pd

from openbi.config.settings import settings
from openbi.ml.forecasting.baseline import moving_average_forecast
from openbi.ml.forecasting.evaluate import compare_models
from openbi.ml.forecasting.exponential_smoothing import ets_forecast
from openbi.ml.forecasting.xgboost_model import xgb_forecast
from openbi.utils.db import load_dataframe, read_sql


HORIZON_MONTHS = 6


def load_monthly_revenue() -> pd.Series:
    """Monthly revenue as a time-indexed Series."""
    sql = """
        SELECT
            MAKE_DATE(year, month, 1) AS month,
            SUM(revenue) AS revenue
        FROM warehouse.v_monthly_revenue
        GROUP BY year, month
        ORDER BY year, month
    """
    df = read_sql(sql)
    df["month"] = pd.to_datetime(df["month"])
    return df.set_index("month")["revenue"].astype(float)


def main() -> None:
    print("=" * 70)
    print("  OpenBI — Sales Forecasting")
    print("=" * 70)

    series = load_monthly_revenue()
    print(f"  Series: {len(series)} months  ({series.index.min().date()} → {series.index.max().date()})")

    # ---- 1. model comparison on holdout ----
    print(f"\n  Comparing models on last {HORIZON_MONTHS} months as holdout...")
    comparison = compare_models(series, holdout_months=HORIZON_MONTHS)
    print(comparison.to_string(index=False))

    winner = comparison.iloc[0]["model"]
    print(f"\n  ✓ Winner: {winner}  (MAPE {comparison.iloc[0]['mape']:.2f}%)")

    # ---- 2. refit winner on full series, produce final forecast ----
    if winner == "baseline_ma":
        final = moving_average_forecast(series, horizon=HORIZON_MONTHS)
    elif winner == "ets":
        final = ets_forecast(series, horizon=HORIZON_MONTHS)
    elif winner == "xgboost":
        final = xgb_forecast(series, horizon=HORIZON_MONTHS)
    else:
        raise ValueError(f"Unknown winner: {winner}")

    # ---- 3. also fit the other two for comparison on the dashboard ----
    all_forecasts = []
    for name, fn in [
        ("baseline_ma", moving_average_forecast),
        ("ets", ets_forecast),
        ("xgboost", xgb_forecast),
    ]:
        try:
            fc = fn(series, horizon=HORIZON_MONTHS)
        except Exception as e:  # noqa: BLE001
            print(f"    skip {name}: {e}")
            continue
        fc = fc.reset_index().rename(columns={"index": "forecast_month"})
        fc["forecast_month"] = pd.to_datetime(fc["forecast_month"])
        fc["model_name"] = name
        fc["is_winner"] = name == winner
        all_forecasts.append(fc)

    out = pd.concat(all_forecasts, ignore_index=True)
    out = out[["forecast_month", "model_name", "yhat",
               "yhat_lower", "yhat_upper", "is_winner"]]
    out["yhat"]       = out["yhat"].round(2)
    out["yhat_lower"] = out["yhat_lower"].round(2)
    out["yhat_upper"] = out["yhat_upper"].round(2)

    load_dataframe(out, table="sales_forecast", schema="warehouse", if_exists="replace")
    print(f"  ✓ Wrote {len(out):,} rows to warehouse.sales_forecast")

    # save comparison report
    report = settings.root / "reports" / "forecast_comparison.csv"
    report.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(report, index=False)
    print(f"  ✓ Saved model comparison: {report.relative_to(settings.root)}")


if __name__ == "__main__":
    main()
