# OpenBI

OpenBI is an end-to-end open-source Business Intelligence and Analytics platform.
It ingests retail transaction data, models it into a star-schema warehouse in
PostgreSQL, exposes KPIs and ML-driven insights through Apache Superset
dashboards, and serves metrics via a FastAPI layer.

## Status

- [x] **Phase 0** — repo scaffold, dataset
- [x] **Phase 1** — EDA, KPI candidate list (`docs/kpi_candidates.md`)
- [x] **Phase 2** — Postgres star schema, ETL pipeline, KPI views
- [x] Phase 3 — Superset dashboards (Executive, Sales)
- [ ] Phase 4 — RFM segmentation + sales forecasting
- [ ] Phase 5 — API, Airflow, tests, CI

## Stack

PostgreSQL · Python · pandas · SQLAlchemy · Apache Superset · scikit-learn · FastAPI · Docker

## Quickstart

```bash
make up      # start Postgres
make init    # run ETL: CSV → staging → warehouse
make psql    # open psql shell
Warehouse schema
text
staging.superstore_raw   ← raw CSV (all text)
     ↓
staging.superstore       ← typed view
     ↓
warehouse.dim_customer
warehouse.dim_product
warehouse.dim_region
warehouse.dim_ship_mode
warehouse.dim_date
warehouse.fact_sales
     ↓
warehouse.v_monthly_revenue
warehouse.v_revenue_by_category
warehouse.v_revenue_by_region
warehouse.v_top_products
warehouse.v_customer_rfm
Verified totals
Metric	Value
Fact rows	9,994
Revenue	$2,297,200.86
Profit	$286,397.02
Customers	793
Products	1,862

## Dashboards

- **Executive Overview** — Revenue, Profit, Orders, Monthly trend
  ![Executive](docs/images/executive_dashboard.png)

- **Sales Intelligence** — Category, Product, Region breakdowns
  ![Sales](docs/images/sales_dashboard.png)

## Access

After `make up` and `make init`:

| Service | URL | Credentials |
|---|---|---|
| Superset | http://localhost:8088 | admin / admin |
| Postgres | localhost:5432 | openbi / openbi |
