# 📊 OpenBI — End-to-End Business Intelligence & Analytics Platform

[![CI](https://github.com/adnanphp/openbi/actions/workflows/ci.yml/badge.svg)](https://github.com/adnanphp/openbi/actions/workflows/ci.yml)
[![CI v2](https://github.com/adnanphp/openbi/actions/workflows/ci-v2.yml/badge.svg)](https://github.com/adnanphp/openbi/actions/workflows/ci-v2.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python\&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql\&logoColor=white)
![Apache Spark](https://img.shields.io/badge/Apache%20Spark-3.5-E25A1C?logo=apachespark\&logoColor=white)
![Kafka](https://img.shields.io/badge/Kafka-3.7-231F20?logo=apachekafka\&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-analytics-FF694B?logo=dbt\&logoColor=white)
![Airflow](https://img.shields.io/badge/Airflow-orchestration-017CEE?logo=apacheairflow\&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi\&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker\&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Kind-326CE5?logo=kubernetes\&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?logo=terraform\&logoColor=white)
![Superset](https://img.shields.io/badge/Apache%20Superset-BI-20A4F3)
![License](https://img.shields.io/badge/License-MIT-green)

> **An open-source, end-to-end Business Intelligence platform combining batch data engineering, stream processing, machine learning, forecasting, dashboards, APIs, monitoring, and Kubernetes deployment.**

OpenBI transforms retail transaction data into a production-style analytics platform.

It operates at multiple scales:

* **v1:** single-node PostgreSQL warehouse processing ~10K rows
* **v2:** distributed Spark + Delta Lake pipeline processing 1M+ rows
* **Streaming:** Kafka + Spark Structured Streaming for real-time events
* **Deployment:** Docker, Kubernetes/Kind, Terraform, and Kustomize

## 🔄 End-to-End Architecture

```text
CSV → ETL → PostgreSQL Star Schema → Analytics → ML → Superset → FastAPI
                       │
                       ├─► Spark + Delta Lake (1M+ rows)
                       ├─► Kafka + Structured Streaming
                       ├─► dbt (SQL transformations + tests)
                       ├─► Airflow (orchestration)
                       ├─► Prometheus + Grafana (monitoring)
                       └─► Kubernetes + Terraform (deployment)
```

---

## 🎯 Executive Summary

|                    | **v1 — PostgreSQL** |  **v2 — Spark + Delta** | **Streaming — Kafka** |
| ------------------ | ------------------: | ----------------------: | --------------------: |
| **Rows processed** |               9,994 |              1,000,000+ |        12,000+ events |
| **Revenue**        |       $2,297,200.86 |         $287,833,061.24 |                  Live |
| **Storage**        |          PostgreSQL | Delta Lake + PostgreSQL |    Delta + PostgreSQL |
| **Compute**        |                 SQL |     PySpark + Spark SQL |  Structured Streaming |
| **Runtime**        |             Seconds |            ~4 min batch |   ~10 s micro-batches |

### Skills Demonstrated

**Data Engineering · Analytics Engineering · Business Intelligence · Machine Learning · Distributed Systems · Stream Processing · DevOps · Cloud-Native Deployment**

**Testing:** 100+ automated checks across unit, integration, data-quality, dbt, Spark, and streaming layers.

**CI/CD:** Two GitHub Actions workflows, both green.

---

## ✨ Key Results

### Business Intelligence — v1

* **7 actionable customer segments** using RFM + KMeans
* **$449K** in historical revenue associated with the At Risk segment
* **15.87% MAPE** using ETS forecasting over a 48-month horizon
* Executive, sales, and customer dashboards in Apache Superset
* FastAPI service exposing analytics and ML results

### Distributed Analytics — v2

* PySpark pipeline processing **1M rows**
* Bronze → Silver → Gold medallion architecture using Delta Lake
* Same dimensional model and BI layer as v1
* Spark MLlib experiments for segmentation and forecasting
* KRR vs MLP experiments documented in the [companion research project](https://github.com/adnanphp/diffusion-hilbert)

### Real-Time Streaming

```text
Kafka (KRaft)
     ↓
Spark Structured Streaming
     ↓
Delta Bronze
     ↓
PostgreSQL
     ↓
Superset Real-Time Dashboard
```

* 10-second micro-batches
* Delta checkpointing for exactly-once processing semantics

### Analytics Engineering

* 6 staging views
* 3 mart tables
* 49 dbt data-quality tests
* Auto-generated dbt lineage DAG

### Kubernetes + Terraform

* 3-node Kind cluster
* Terraform-based cluster provisioning
* Kustomize-based application deployment
* One-command deployment:

```bash
make k8s-up
```

---

# 🏗️ Architecture

## v1 — Single Node

```text
CSV
 │
 ▼
Staging
 │
 ▼
PostgreSQL Star Schema
(5 dimensions + 1 fact)
 │
 ├──────────────┬──────────────┐
 ▼              ▼              ▼
KPIs           RFM        Forecasting
 │              │              │
 └──────────────┼──────────────┘
                ▼
        ┌───────┴───────┐
        ▼               ▼
    Superset          FastAPI
```

## v2 — Distributed Spark + Delta Lake

```text
Parquet (1M rows)
       │
       ▼
PySpark Ingestion
       │
       ▼
Delta Bronze
(partitioned by category)
       │
       ▼
Delta Silver
Star Schema
(partitioned by year)
       │
       ▼
Gold Aggregations
       │
       ▼
PostgreSQL warehouse_big
       │
       ├── Spark MLlib
       │   ├── RFM + KMeans
       │   └── Forecasting
       │
       └── Superset + FastAPI
```

## Real-Time Streaming

```text
producer.py
     │
     ▼
Kafka
(topic: orders)
     │
     ▼
Spark Structured Streaming
     │
     ▼
Delta Bronze
     │
     ▼
warehouse_big.orders_realtime
     │
     ▼
Superset Real-Time Dashboard
```

## Kubernetes — Kind + Terraform

```text
Terraform
    │
    ▼
Kind Cluster
(1 control-plane + 2 workers)
    │
    ▼
kubectl apply -k infrastructure/kubernetes/
    │
    ├──────────────┬──────────────┐
    ▼              ▼              ▼
PostgreSQL      FastAPI        Superset
  + PVC         2 replicas     + PVC + init
```

Detailed architecture documentation:

* [Big Data Architecture](docs/architecture_bigdata.md)
* [Monitoring](docs/monitoring.md)
* [dbt](docs/dbt.md)
* [Streaming](docs/streaming.md)
* [Kubernetes](docs/kubernetes.md)

---

# 🧰 Technology Stack

| **Layer**             | **Technologies**                          |
| --------------------- | ----------------------------------------- |
| **Language**          | Python 3.12                               |
| **Data Processing**   | Pandas · NumPy · PySpark                  |
| **Databases**         | PostgreSQL · Delta Lake / Parquet         |
| **Batch Compute**     | Spark · PySpark · Spark SQL · Spark MLlib |
| **Stream Processing** | Kafka · Spark Structured Streaming        |
| **Orchestration**     | Apache Airflow · Make                     |
| **Transformation**    | dbt                                       |
| **BI / Dashboards**   | Apache Superset                           |
| **ML / Forecasting**  | scikit-learn · XGBoost · statsmodels      |
| **API**               | FastAPI · Pydantic                        |
| **Monitoring**        | Prometheus · Grafana · statsd-exporter    |
| **Testing**           | pytest                                    |
| **CI/CD**             | GitHub Actions                            |
| **Containers**        | Docker · Docker Compose                   |
| **Deployment**        | Kubernetes / Kind · Terraform · Kustomize |

---

# 🚀 Quickstart

## Prerequisites

* Docker + Docker Compose
* Python 3.12
* Make
* Optional: Kind, Terraform, kubectl

## Local Development — v1

```bash
git clone https://github.com/adnanphp/openbi.git
cd openbi

pip install -r requirements.txt
pip install -e .

make up
make init
```

The initialization command runs the v1 ETL and ML pipeline end-to-end.

### Services

* **Superset:** http://localhost:8088
* **FastAPI:** http://localhost:8000/docs

Default Superset credentials:

```text
Username: admin
Password: admin
```

---

## Distributed Analytics — v2

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.bigdata.yml up -d

make bigdata
make bigdata-ml
make bigdata-test
```

Pipeline:

```text
Bronze → Silver → Gold → PostgreSQL
```

---

## Real-Time Streaming

Start Kafka and create the required topic:

```bash
make streaming-up
```

Then run the streaming pipeline:

```bash
# Terminal 1
python -m streaming.producer --rate 5

# Terminal 2
make streaming-bronze

# Terminal 3
make streaming-postgres

# Terminal 4
make streaming-status
```

---

## dbt Transformations

```bash
make dbt-build
make dbt-docs
```

This runs the dbt models and associated data-quality tests.

The generated documentation server is available at:

```text
http://localhost:8085
```

---

## Kubernetes Deployment

```bash
make k8s-up
make k8s-status
make k8s-down
```

`make k8s-up` provisions the Kind cluster through Terraform and applies the Kubernetes manifests.

---

# 📈 Results

## Business Metrics — v1

| **Metric**    |         **Value** |
| ------------- | ----------------: |
| Total revenue | **$2,297,200.86** |
| Total profit  |   **$286,397.02** |
| Profit margin |        **12.47%** |
| Orders        |         **5,009** |
| Customers     |           **793** |
| Products      |         **1,862** |

## Distributed Metrics — v2

| **Layer**           |  **Rows** | **Notes**                        |
| ------------------- | --------: | -------------------------------- |
| Delta Bronze        | 1,000,000 | Partitioned by category          |
| Delta Silver        | 1,000,000 | Star schema, partitioned by year |
| Delta Gold          |     1,251 | 5 pre-aggregated KPI tables      |
| `warehouse_big`     |     1,251 | JDBC-published                   |
| `customer_segments` |       800 | 7 RFM segments                   |
| `sales_forecast`    |        18 | 3 models × 6 months              |

---

## Customer Segmentation

RFM features are clustered using KMeans and mapped to business-friendly segment names.

| **Segment**         | **Customers** | **Recency** | **Frequency** | **Monetary** |
| ------------------- | ------------: | ----------: | ------------: | -----------: |
| Champions           |           106 |         25d |           9.3 |       $5,288 |
| At Risk             |           102 |        220d |           7.8 |       $4,400 |
| Loyal Customers     |            92 |         55d |           8.6 |       $3,426 |
| Potential Loyalists |           116 |         27d |           6.2 |       $2,731 |
| Need Attention      |           221 |        167d |           5.4 |       $2,297 |
| New Customers       |            39 |         25d |           3.3 |       $1,421 |
| Lost                |           117 |        386d |           3.4 |         $794 |

**Key insight:** The **At Risk** segment represents approximately **$449K in historical revenue**, making it the primary win-back opportunity identified by the analysis.

---

## Sales Forecasting

| **Model**                 |   **MAPE** |   **RMSE** |
| ------------------------- | ---------: | ---------: |
| 🥇 **ETS (Holt-Winters)** | **15.87%** | **15,885** |
| XGBoost                   |     28.85% |     34,769 |
| Moving Average            |     38.66% |     41,460 |

The pipeline selects the winning model automatically based on holdout MAPE.

---

# 🌐 FastAPI Service

Start the API:

```bash
uvicorn openbi.api.main:app --reload --port 8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

## Endpoints

| **Endpoint**                | **Description**                  |
| --------------------------- | -------------------------------- |
| `GET /health`               | Liveness check                   |
| `GET /kpis/executive`       | Revenue, profit, orders, margin  |
| `GET /kpis/monthly-revenue` | 48-month revenue trend           |
| `GET /kpis/by-category`     | Revenue by product category      |
| `GET /customers/segments`   | RFM segments and aggregates      |
| `GET /forecasts/latest`     | Winning model's 6-month forecast |
| `GET /forecasts/models`     | All candidate forecasting models |

Example:

```bash
curl -s http://localhost:8000/customers/segments | jq
```

Example response:

```json
[
  {
    "cluster_label": "Champions",
    "customers": 106,
    "avg_monetary": 5287.72
  },
  {
    "cluster_label": "At Risk",
    "customers": 102,
    "total_monetary": 448760.00
  }
]
```

---

# 🗄️ Data Warehouse

## v1 — PostgreSQL Star Schema

```text
warehouse/
├── dim_customer
├── dim_product
├── dim_region
├── dim_ship_mode
├── dim_date
├── fact_sales
├── v_monthly_revenue
├── v_revenue_by_category
├── v_revenue_by_region
├── v_top_products
└── v_customer_rfm
```

## v2 — Delta Lake Medallion + PostgreSQL Serving

```text
data/bronze/sales/      ← Delta, partitioned by category
data/silver/dim_*/      ← Delta, star schema
data/silver/fact_sales/ ← Delta, partitioned by year
data/gold/*/            ← Delta, 5 KPI tables
warehouse_big.*         ← PostgreSQL, JDBC-published
```

---

# 🧪 Testing

Run the different test layers with:

```bash
pytest tests -v
make bigdata-test
make dbt-test
```

| **Layer**                  | **Scope**                                |
| -------------------------- | ---------------------------------------- |
| `tests/unit/`              | Forecasting, RFM, KPI calculations       |
| `tests/integration/`       | Warehouse totals, API endpoints          |
| `tests/data_quality/`      | Nulls, uniqueness, referential integrity |
| `spark/tests/`             | Silver, Gold, and ML tests               |
| `dbt/models/**/schema.yml` | dbt data-quality tests                   |

### Test Coverage

**100+ automated checks** across the project, with both CI workflows configured to run automatically.

---

# 📊 Dashboards

Apache Superset provides four main analytical views:

### Executive

Revenue, profit, margin, and monthly trends.

### Sales

Category, region, and product-level drill-downs.

### Customer

RFM segments, revenue by segment, and customer risk.

### Real-Time Orders

Live events flowing through the Kafka → Spark Structured Streaming pipeline.

Screenshots are available in [`docs/images/`](docs/images/).

---

# 📚 Documentation

| **Document**                                                   | **Topic**                     |
| -------------------------------------------------------------- | ----------------------------- |
| [`docs/architecture_bigdata.md`](docs/architecture_bigdata.md) | v2 Spark + Delta architecture |
| [`docs/gold_schema.md`](docs/gold_schema.md)                   | Gold-layer schema             |
| [`docs/ml_schema.md`](docs/ml_schema.md)                       | ML output tables              |
| [`docs/monitoring.md`](docs/monitoring.md)                     | Prometheus + Grafana          |
| [`docs/dbt.md`](docs/dbt.md)                                   | dbt models + tests            |
| [`docs/streaming.md`](docs/streaming.md)                       | Kafka + Structured Streaming  |
| [`docs/kubernetes.md`](docs/kubernetes.md)                     | Kubernetes + Terraform        |

---

# 📁 Repository Structure

```text
openbi/
├── src/openbi/
│   ├── ingestion/            # CSV → staging
│   ├── etl/                  # ETL pipeline
│   ├── analytics/            # RFM, KPIs
│   ├── ml/                   # Segmentation, forecasting
│   ├── api/                  # FastAPI service
│   ├── metrics/              # Prometheus exporter
│   └── orchestration/dags/   # Airflow DAGs
│
├── spark/
│   ├── jobs/                 # Bronze → Silver → Gold → ML
│   └── tests/                # Spark tests
│
├── dbt/                      # dbt models + tests
├── streaming/                # Kafka producer
├── sql/                      # DDL + transformations + views
├── docker/                   # Per-service Dockerfiles
├── monitoring/               # Prometheus + Grafana
├── airflow/                  # Airflow DAGs
│
├── infrastructure/
│   ├── terraform/            # Kind cluster provisioning
│   └── kubernetes/           # Kustomize manifests
│
├── tests/                    # v1 test suite
├── docs/                     # Documentation + screenshots
└── Makefile                  # One-command workflows
```

---

# 🧠 Design Decisions

### Historical RFM Anchor

Recency is anchored to the **last order in the dataset**, rather than `CURRENT_DATE`, preventing historical customers from being incorrectly classified as stale.

### Translation at Ingestion

The Portuguese Superstore CSV variant is translated to English during ingestion in `load_csv.py`, keeping downstream SQL and analytics readable.

### Business-Friendly Segment Labels

KMeans cluster IDs are mapped to meaningful business labels such as **Champions**, **At Risk**, and **Loyal Customers** using RFM-based rules rather than exposing arbitrary cluster numbers.

### Idempotent Pipelines

SQL operations use `IF NOT EXISTS` or `DROP ... CASCADE`, allowing `make init` to be rerun reproducibly.

### Two-Tier Warehouse

v1 uses PostgreSQL under `warehouse.*`.

v2 uses Delta Lake with PostgreSQL serving under `warehouse_big.*`.

The BI layer can work against either warehouse schema without requiring changes to the analytical layer.

### Local Streaming, Distributed Batch

Kafka micro-batches are small, so the PostgreSQL streaming sink uses `--master local[2]`.

The two-worker Spark cluster is reserved for heavier batch workloads.

### Kind over Minikube

Kind runs Kubernetes nodes as Docker containers, making it lightweight and convenient for local development and CI. Terraform provisions the cluster, while Kustomize manages workloads.

---

# 🎯 What This Project Demonstrates

* ✅ **Data engineering** — ETL, orchestration, distributed pipelines
* ✅ **Analytics engineering** — dbt, dimensional modeling, data-quality testing
* ✅ **Business intelligence** — KPI design, dashboards, drill-down analysis
* ✅ **Machine learning** — RFM + KMeans, time-series forecasting
* ✅ **Stream processing** — Kafka + Structured Streaming
* ✅ **Backend engineering** — FastAPI, Pydantic, REST APIs
* ✅ **Observability** — Prometheus metrics and Grafana dashboards
* ✅ **DevOps** — Docker Compose, CI pipelines, multi-service deployment
* ✅ **Infrastructure as Code** — Terraform, Kubernetes, Kustomize
* ✅ **Reproducibility** — one-command workflows across multiple layers

---

# 📄 License

MIT License — see [`LICENSE`](LICENSE).

---

<p align="center">
  <b>OpenBI</b> · Open-source Business Intelligence & Analytics
  <br>
  <sub>
    Python · PostgreSQL · Spark · Delta Lake · Kafka · dbt · Airflow ·
    Superset · FastAPI · Prometheus · Kubernetes
  </sub>
</p>
