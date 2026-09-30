# OpenBI v2 — Monitoring

Prometheus + Grafana stack for observing the big data pipeline.

## Services

| Service | Port | Purpose |
|---|---|---|
| Prometheus | 9090 | Metrics TSDB + alerting |
| Grafana | 3000 | Dashboards |
| statsd-exporter | 9125/udp, 9102 | Bridges Airflow's statsd → Prometheus |
| openbi-exporter | 9103 | Custom exporter for data/ML metrics |

## Metrics exposed

### From openbi-exporter
- `openbi_fact_sales_rows` — Silver fact row count
- `openbi_monthly_revenue_rows` — Gold monthly aggregate
- `openbi_customer_segments_rows` — ML output row count
- `openbi_sales_forecast_rows` — forecast row count
- `openbi_data_freshness_seconds` — seconds since last pipeline run
- `openbi_segment_size{label="Champions"}` — customers per RFM segment
- `openbi_forecast_mape` — current model MAPE

### From Airflow (via statsd)
- `airflow_dag_duration_seconds{dag_id,state}`
- `airflow_task_duration_seconds{dag_id,task_id,state}`
- `airflow_scheduler_heartbeat_total`
- `airflow_executor_total{state}`

## Alerts

Defined in `monitoring/prometheus/alerts.yml`:

| Alert | Condition | Severity |
|---|---|---|
| OpenBIDataStale | Freshness > 25h | warning |
| OpenBIFactRowsDropping | Negative delta > 1000 in 1h | critical |
| OpenBIForecastMAPEHigh | MAPE > 50% for 30m | warning |
| AirflowSchedulerDown | Prometheus scrape of Airflow fails 5m | critical |

## Access

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (anonymous read-only; admin/admin for edit)
- **Raw metrics**: `curl http://localhost:9103/metrics`

## Start / stop

```bash
make monitoring-up
make monitoring-down
Design
openbi-exporter queries Postgres directly on every scrape (30s), so
data metrics reflect the live warehouse state.

statsd-exporter is the bridge between Airflow and Prometheus — Airflow
natively emits statsd UDP, and the exporter maps those to Prometheus format.

Grafana auto-provisions the Prometheus datasource and the OpenBI
dashboard from monitoring/grafana/.

Adding a metric
Add a Gauge(...) to src/openbi/metrics/exporter.py

Add the SQL query to QUERIES in the same file

Update monitoring/grafana/dashboards/openbi_pipeline.json to visualize it

Restart the exporter: docker compose restart openbi-exporter
