# OpenBI — Gold Layer (Delta + Postgres)

The Gold layer aggregates the 1M-row Silver fact table into small,
pre-computed tables that power Superset and FastAPI at v2 scale.

## Pipeline
data/silver/fact_sales/ (Delta, 1M rows)
│
│ PySpark groupBy
▼
data/gold/ (Delta)
monthly_revenue 96 rows
revenue_by_category 17 rows
revenue_by_region 196 rows
top_products 100 rows
customer_rfm 800 rows
│
│ Spark JDBC write
▼
warehouse_big.* (Postgres) ← served to Superset + FastAPI

text

## Design

**Delta** is source of truth — cheap to recompute, time-travel, and rerun.
**Postgres** is the serving layer — low-latency BI queries on the same column
names v1 used.

Superset and FastAPI don't know whether they're reading v1 or v2 — they just
see the same column names in a different schema.

## v1 vs v2 comparison

| Metric | v1 (Postgres) | v2 (Spark) |
|---|---:|---:|
| Source rows | 9,994 | 1,000,000 |
| Revenue | $2,297,200.86 | $287,833,061.24 |
| Profit | $286,397.02 | (see monthly table) |
| Customers | 793 | 800 |
| Products | 1,862 | 1,900 |
| Runtime (full pipeline) | ~10 s | ~4 min |

## Tables

### monthly_revenue
`year, month, month_name, revenue, profit, orders, avg_line_value`
96 rows (8 years × 12 months).

### revenue_by_category
`category, sub_category, revenue, profit, units` — 17 rows.

### revenue_by_region
`region, state, revenue, profit` — 196 rows (US states × regions).

### top_products
`product_id, product_name, category, revenue, profit, units` — top 100 by revenue.

### customer_rfm
`customer_id, customer_name, segment, recency_days, frequency, monetary, r_score, f_score, m_score, rfm_score, cluster_label` — 800 rows.

## Running

```bash
make bigdata            # bronze → silver → gold → postgres
make bigdata-test       # run all tests
Or run individual steps:

bash
./spark/run_job.sh jobs/silver_to_gold.py
./spark/run_job.sh jobs/publish_to_postgres.py
