[![CI](https://github.com/adnanphp/openbi/actions/workflows/ci.yml/badge.svg)](https://github.com/adnanphp/openbi/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

# OpenBI — End-to-End Business Intelligence & Analytics Platform

An open-source BI + ML platform that ingests retail transaction data, models it
into a Postgres star schema, generates ML-driven customer segments and sales
forecasts, exposes KPIs through Apache Superset dashboards and a FastAPI
service, and runs the full pipeline through Docker Compose.

**Stack:** Python · PostgreSQL · SQLAlchemy · Apache Superset · scikit-learn ·
XGBoost · statsmodels · FastAPI · Docker · GitHub Actions

---

## 📌 Highlights

- **9,994 rows** ingested and validated end-to-end (revenue total matches source: **$2,297,200.86**)
- **6 dimension + fact tables**, **5 KPI views**, fully reproducible with `make init`
- **RFM segmentation** with KMeans surfacing **7 business segments**, including **$449K in "At Risk" revenue**
- **Sales forecasting** comparing baseline / ETS / XGBoost — **ETS wins at 15.87% MAPE** on 48-month horizon
- **3 Apache Superset dashboards** (Executive · Sales · Customer)
- **FastAPI service** exposing KPIs, segments, and forecasts as JSON
- **27 tests** across unit, integration, and data-quality layers — **CI green**

---

## 🏗️ Architecture

```text
                 ┌───────────────────────────┐
                 │  data/raw/superstore.csv  │
                 └────────────┬──────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Python ingestion │  (PT→EN translation, type coercion)
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  staging.superstore_raw │
                    └─────────┬─────────┘
                              │
                 ┌────────────▼─────────────┐
                 │  warehouse (star schema) │
                 │  dims: customer, product,│
                 │        region, ship_mode,│
                 │        date              │
                 │  fact: fact_sales        │
                 └────────────┬─────────────┘
                              │
              ┌───────────────┼────────────────┐
              │               │                │
    ┌─────────▼─────────┐  ┌──▼─────────────┐  ┌▼──────────────────┐
    │  KPI views        │  │  ML: RFM +     │  │  ML: Forecasting  │
    │  v_monthly_revenue│  │  KMeans        │  │  baseline / ETS / │
    │  v_revenue_by_*   │  │  → customer_   │  │  XGBoost          │
    │  v_customer_rfm   │  │    segments    │  │  → sales_forecast │
    └─────────┬─────────┘  └──┬─────────────┘  └┬──────────────────┘
              │               │                │
              └───────────────┼────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
        ┌───────▼────────┐         ┌────────▼────────┐
        │ Apache Superset│         │  FastAPI  /docs │
        │  3 dashboards  │         │  /kpis /customers│
        │                │         │  /forecasts     │
        └────────────────┘         └─────────────────┘
🚀 Quickstart
Prerequisites: Docker, Python 3.12

bash
# 1. clone
git clone https://github.com/adnanphp/openbi.git
cd openbi

# 2. install Python deps
pip install -r requirements.txt
pip install -e .

# 3. start Postgres + Superset
make up

# 4. run ETL (CSV → warehouse)
make etl

# 5. run ML (segmentation + forecasting)
make ml

# 6. explore
#    Superset:  http://localhost:8088   (admin / admin)
#    API docs:  http://localhost:8000/docs
Re-run everything end-to-end:

bash
make init         # up + wait-db + etl + ml
make test         # run test suite
make cov          # tests with coverage
make clean        # tear down containers + volumes
📈 Key Insights
Revenue & Profit (2014–2017)
Metric	Value
Total revenue	$2,297,200.86
Total profit	$286,397.02
Profit margin	12.47%
Orders	5,009
Customers	793
Products	1,862
RFM Customer Segmentation
KMeans (k=5) on standardized Recency/Frequency/Monetary, with rule-based labels.

Segment	Customers	Avg Recency	Avg Frequency	Avg Monetary
Champions	106	25 days	9.3	$5,288
At Risk ⚠️	102	220 days	7.8	$4,400
Loyal Customers	92	55 days	8.6	$3,426
Potential Loyalists	116	27 days	6.2	$2,731
Need Attention	221	167 days	5.4	$2,297
New Customers	39	25 days	3.3	$1,421
Lost	117	386 days	3.4	$794
Actionable finding: the At Risk segment represents $449K in historical
revenue from 102 customers who used to buy at Champions-level frequency
but have gone ~7 months without a purchase. This is the highest-priority
win-back cohort.

Sales Forecasting
48-month horizon, 6-month holdout, model selection by MAPE.

Model	MAPE	RMSE
ETS (Holt-Winters) 🏆	15.87%	15,885
XGBoost (lag features)	28.85%	34,769
Baseline (moving avg)	38.66%	41,460
ETS wins on this short series. XGBoost underperforms — a common result
when training signal is limited. The pipeline picks the winner automatically.

🌐 API
FastAPI service with auto-generated Swagger docs at /docs.

bash
uvicorn openbi.api.main:app --reload --port 8000
Endpoint	Returns
GET /health	Liveness
GET /kpis/executive	Revenue, profit, orders, AOV, margin
GET /kpis/monthly-revenue	48 months of revenue + profit
GET /kpis/by-category	Revenue by product category
GET /customers/segments	RFM segments with aggregates
GET /forecasts/latest	Winning model's 6-month forecast
GET /forecasts/models	All candidate models' forecasts
Example:

bash
curl -s http://localhost:8000/customers/segments | jq
json
[
  { "cluster_label": "Champions", "customers": 106, "avg_monetary": 5287.72, ... },
  { "cluster_label": "At Risk",   "customers": 102, "total_monetary": 448,760.00, ... }
]
🗄️ Warehouse Schema
Staging (raw landing)

text
staging.superstore_raw      -- all text, faithful to source CSV
staging.superstore          -- typed view (dates, numerics)
Warehouse (star schema)

text
warehouse.dim_customer      customer_id, name, segment
warehouse.dim_product       product_id, name, category, sub_category
warehouse.dim_region        country, region, state, city, postal
warehouse.dim_ship_mode     ship_mode
warehouse.dim_date          calendar (year → is_weekend)
warehouse.fact_sales        order grain, FK to all dims

warehouse.v_monthly_revenue        KPI view
warehouse.v_revenue_by_category    KPI view
warehouse.v_revenue_by_region      KPI view
warehouse.v_top_products           KPI view
warehouse.v_customer_rfm           KPI view

warehouse.customer_segments        ML output (RFM + KMeans)
warehouse.sales_forecast           ML output (3 models × 6 months)
warehouse.v_forecast_vs_actual     dashboard union view
🧪 Testing
bash
pytest tests -v
Layer	Scope
tests/unit/	Forecasting math, RFM scoring, KPI formulas
tests/integration/	Warehouse totals, API endpoints
tests/data_quality/	Nulls, uniqueness, referential integrity
27 tests · CI runs on every push.

🐳 Running the Full Stack
bash
docker compose up -d
Service	Port	Purpose
postgres	5432	Data warehouse + Superset metadata
superset	8088	BI dashboards
(api)	8000	FastAPI (uvicorn on host)
(airflow)	8080	DAG runner (optional)
📁 Repository Layout
text
openbi/
├── src/openbi/              # main Python package
│   ├── ingestion/           # CSV → staging
│   ├── etl/                 # pipeline orchestration
│   ├── analytics/           # RFM, KPIs
│   ├── ml/
│   │   ├── segmentation/    # KMeans on RFM
│   │   └── forecasting/     # baseline, ETS, XGBoost
│   ├── api/                 # FastAPI service
│   └── orchestration/dags/  # Airflow DAGs
├── sql/                     # DDL + transforms + KPI views
├── docker/                  # Postgres + Superset images
├── tests/                   # unit + integration + quality
├── docs/images/             # dashboard screenshots
├── notebooks/               # EDA, RFM exploration
└── Makefile                 # up · etl · ml · test · cov
🛠️ Design Decisions
Anchor RFM recency to the last order in the data, not CURRENT_DATE. Historical datasets (like Superstore) would otherwise show every customer as "386+ days stale."

Translate the Portuguese Superstore variant → English inside load_csv.py so downstream SQL stays clean.

Rule-based segment labels on top of KMeans clusters. Sorting centroids by an arbitrary formula produces misleading labels; standard RFM rules are defensible in business conversations.

Idempotent SQL: every CREATE uses IF NOT EXISTS, every DROP uses CASCADE. The pipeline can be re-run safely.

CI includes a fresh-venv import check — prevents "works on my machine" class bugs.

📄 License
MIT
