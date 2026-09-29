# OpenBI — Big Data Architecture (v2)

## Overview

OpenBI v1 ran on a single-node Postgres warehouse (10K rows, pandas ETL).
v2 extends the same platform to **distributed scale (100M+ rows)** by adding
PySpark as the compute engine, Delta Lake for ACID storage, and Airflow for
orchestration — while keeping Superset, the FastAPI service, and the star
schema unchanged.

## Layered architecture
┌────────────────────────┐
│ Raw Parquet │
│ data/raw/big_superstore│
│ ~100M rows / ~15 GB │
└───────────┬────────────┘
│ Spark read
┌───────────▼────────────┐
│ BRONZE (Delta) │
│ data/bronze/sales/ │
│ raw + metadata cols │
│ partitioned by category│
└───────────┬────────────┘
│ Spark SQL
┌───────────▼────────────┐
│ SILVER (Delta) │
│ dims + fact_sales │
│ partitioned by year │
└───────────┬────────────┘
│
┌─────────────────┼─────────────────┐
│ │ │
┌─────────▼─────────┐ ┌────▼──────────┐ ┌───▼──────────────┐
│ GOLD (Delta) │ │ Spark MLlib │ │ Analytics SQL │
│ KPI aggregations │ │ RFM + KMeans │ │ v_* views │
│ pre-computed │ │ Forecasting │ │ │
└─────────┬─────────┘ └────┬──────────┘ └───┬──────────────┘
│ │ │
└────────────────┼────────────────┘
│ JDBC write
┌──────────▼──────────┐
│ PostgreSQL (sink) │
│ small aggregates │
│ for BI layer │
└──────────┬──────────┘
│
┌──────────▼──────────┐
│ Superset + FastAPI │
│ (unchanged from v1)│
└─────────────────────┘
▲
│
┌──────────┴──────────┐
│ Airflow │
│ batch DAG │
│ ML DAG │
└─────────────────────┘

text

## Why Delta Lake

- **ACID transactions** on top of Parquet — safe concurrent reads/writes
- **Time travel** — query any prior version of a table
- **Schema evolution** — `mergeSchema` handles new columns
- **Upserts** — `MERGE INTO` for slowly-changing dimensions
- **Ecosystem** — first-class PySpark support, well-documented

## Spark cluster topology

| Service | Role | Resources | Web UI |
|---|---|---|---|
| spark-master | Coordinator | 2 GB, 2 cores | :8080 |
| spark-worker-1 | Executor | 2 GB, 2 cores | :8081 |
| spark-worker-2 | Executor | 2 GB, 2 cores | :8082 |

Total: 4 GB executor memory, 4 executor cores.

## Data flow (Phase A: Bronze only)

1. `scripts/generate_big_dataset.py` produces raw Parquet (~100M rows)
2. `spark/jobs/ingest_to_bronze.py` reads Parquet, adds metadata, writes Delta
3. Delta table is partitioned by `category` for fast category-scoped queries

Later phases add:

- Phase B — `bronze_to_silver.py` (dims + fact, partitioned by year)
- Phase C — `silver_to_gold.py` (KPI aggregates) + `publish_to_postgres.py`
- Phase D — `ml_rfm_kmeans.py`, `ml_forecast.py` (Spark MLlib)
- Phase E — Airflow DAGs orchestrating the whole pipeline
- Phase F — CI running Spark in local mode + tests

## Running locally

```bash
# start the big-data stack
docker compose -f docker-compose.yml -f docker-compose.bigdata.yml up -d

# check cluster
open http://localhost:8080

# run the Bronze ingestion
./spark/run_job.sh jobs/ingest_to_bronze.py --source parquet
Design decisions
Partitioning by category in Bronze matches the most common filter in
downstream queries. Partition pruning is 3–10× faster than full scans.

Delta over plain Parquet because dimension updates (slowly-changing
customers) need MERGE — Parquet alone can't do upserts.

Postgres remains the serving layer. Superset and FastAPI in v1 stay
untouched. Only the pipeline changes, not the consumption layer.

File layout mirrors the lakehouse pattern (bronze/silver/gold) so the
mental model transfers to Databricks, Snowflake, and Iceberg-based stacks.

What stays the same from v1
Star schema (5 dims + 1 fact)

KPI definitions (sql/06_views_kpis.sql maps 1:1 to Spark SQL)

Superset dashboards — no changes

FastAPI endpoints — no changes

Test philosophy (unit + integration + data-quality)

What changes
Compute: pandas → PySpark

Storage: Postgres tables → Delta Lake (Parquet + log)

Orchestration: scripts → Airflow

ML: scikit-learn → Spark MLlib

Scale: 10K rows → 100M+ rows
