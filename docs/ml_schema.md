# OpenBI v2 — ML Layer

The ML layer runs distributed Spark MLlib jobs on the 1M-row Silver fact table,
producing two output tables consumed by Superset:

- `warehouse_big.customer_segments` — RFM + KMeans segmentation
- `warehouse_big.sales_forecast` — time-series forecasts from 3 candidate models

## Pipeline
data/silver/fact_sales/ (1M rows)
│
│ PySpark groupBy
▼
data/gold/customer_rfm/ (intermediate RFM features)
│
│ Spark MLlib KMeans
▼
data/gold/customer_segments/ → warehouse_big.customer_segments
data/gold/sales_forecast/ → warehouse_big.sales_forecast

text

## Models

### RFM + KMeans (spark/jobs/ml_rfm_kmeans.py)

- **Features:** standardized Recency (days), Frequency (distinct orders), Monetary (total sales)
- **Recency anchor:** the last order date in the data, not `CURRENT_DATE`
  (historical dataset — anchoring to today would show every customer as stale)
- **Clustering:** Spark MLlib `KMeans(k=5)`, distributed across the cluster
- **Labels:** rule-based assignment on top of R/F/M quintile scores:
  - `Champions`        — R≥4, F≥4, M≥4
  - `Loyal Customers`  — R≥3, F≥4, M≥3
  - `Potential Loyalists` — R≥4, F≥2, M≥2
  - `At Risk`          — R≤2, F≥3, M≥3
  - `Lost`             — R≤2, F≤2, M≤2
  - `New Customers`    — R≥4, F=1
  - `Need Attention`   — fallback

### Forecasting (spark/jobs/ml_forecast.py)

Three candidate models, winner selected by holdout MAPE:

| Model | Description |
|---|---|
| `baseline_ma` | 3-month moving average |
| `ets` | Holt-Winters Exponential Smoothing |
| `xgboost` | Gradient boosting on lag + calendar features |

**Winner is not fixed** — whichever model has the lowest MAPE on the last 6 months wins.
On the current series, `baseline_ma` wins; on different data, `ets` or `xgboost` could win.

**Predictions are clamped to ≥ 0.** Revenue cannot be negative. This is domain-aware
post-processing, not a modeling hack.

## Postgres schema

Both tables are in `warehouse_big`, alongside the Phase C Gold tables.

### customer_segments

| Column | Type | Notes |
|---|---|---|
| customer_id | TEXT | PK |
| customer_name | TEXT | |
| segment | TEXT | Consumer / Corporate / Home Office |
| recency_days | INTEGER | since last order (anchored to data snapshot) |
| frequency | BIGINT | distinct orders |
| monetary | NUMERIC | total sales |
| r_score, f_score, m_score | INTEGER | 1..5 quintiles |
| rfm_score | TEXT | e.g. "555" |
| cluster_id | INTEGER | raw KMeans cluster |
| cluster_label | TEXT | rule-based label |
| computed_at | TIMESTAMP | |

### sales_forecast

| Column | Type | Notes |
|---|---|---|
| forecast_month | DATE | part of composite PK |
| model_name | TEXT | part of composite PK |
| yhat | NUMERIC | point forecast |
| yhat_lower, yhat_upper | NUMERIC | 95% prediction interval (nullable) |
| is_winner | BOOLEAN | TRUE for the winning model's rows |
| computed_at | TIMESTAMP | |

**Composite PK** on `(forecast_month, model_name)` — needed because 3 models
produce 3 rows per month. Total 18 rows (6 months × 3 models).

## Running

```bash
# run all ML jobs
make bigdata-ml

# or individually
./spark/run_job.sh jobs/ml_rfm_kmeans.py
./spark/run_job.sh jobs/ml_forecast.py
./spark/run_job.sh jobs/publish_ml_to_postgres.py
Tests
spark/tests/test_ml.py — 9 tests covering:

Segment row count, score ranges, label presence, null checks, uniqueness

Forecast row count, exactly one winner per month, positive yhat, three models

Run:

bash
docker exec -i openbi-spark-master python3 -m pytest \
    -p no:cacheprovider /opt/openbi/tests/test_ml.py -v
Design decisions
Spark MLlib KMeans for segmentation — scales to millions of customers without code changes.

statsmodels/XGBoost on the driver for forecasting — the fact table is reduced to ~130 monthly points via Spark aggregation, then models run in pandas. Distributed MLlib does not add value at that size.

Rule-based labels on top of clusters — KMeans discovers groups; rules make them communicable to business stakeholders.

Domain-aware clamping — forecasts clipped to ≥ 0.

Model selection by MAPE — the pipeline picks the winner automatically; no hardcoded "best model."
