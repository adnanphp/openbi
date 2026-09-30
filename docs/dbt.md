# OpenBI — dbt Analytics Layer

dbt sits on top of the Spark-produced `warehouse_big` tables and produces
curated marts for Superset.

## Architecture
Spark (Delta, 1M rows)
│
│ publish_.py
▼
Postgres warehouse_big.
│
│ dbt sources
▼
dbt staging (6 views)
│
│ ref()
▼
dbt marts (3 tables)
│
▼
Superset

text

## Models

### Staging (views)
- `stg_monthly_revenue`
- `stg_revenue_by_category`
- `stg_revenue_by_region`
- `stg_top_products`
- `stg_customer_segments`
- `stg_sales_forecast`

### Marts (tables)
- `mart_executive_kpis` — yearly revenue, profit, margin, YoY
- `mart_customer_intelligence` — per-segment customers, revenue share
- `mart_forecast_performance` — winning model forecast + uncertainty bands

## Tests

21 data-quality tests:
- `not_null` — key columns
- `unique` — dimension keys
- `accepted_values` — segment labels, model names
- `expression_is_true` — non-negative revenue, valid percentages

## Run

```bash
make dbt-build       # deps + run + test
make dbt-run         # models only
make dbt-test        # tests only
make dbt-docs        # generate docs
make dbt-docs-serve  # serve docs at :8080
View the lineage
After make dbt-docs && make dbt-docs-serve:

http://localhost:8080

Click the green icon at the bottom-right of any model to see the DAG.

Design decisions
dbt on Postgres, not Delta. Spark already handles 1M-row transforms;
dbt's job is to build curated views/marts on the small serving layer.

Staging = views, marts = tables. Views are cheap and always current;
marts are materialized for Superset query speed.

Schema separation. analytics_staging and analytics_marts keep
dbt's outputs isolated from Spark's warehouse_big.

Tests as code. Column-level tests run in parallel with dbt test.
