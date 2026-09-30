"""OpenBI — Prometheus exporter for data and ML metrics.

Runs as a small HTTP server on :9103. Every scrape, it queries Postgres
for current row counts, freshness, and model metrics, and exposes them
as Prometheus gauges.

Run:
    python -m openbi.metrics.exporter

Scraped by Prometheus at:
    http://openbi-exporter:9103/metrics
"""

from __future__ import annotations

import os
import time

from prometheus_client import Gauge, start_http_server
from sqlalchemy import text

from openbi.utils.db import get_engine


# ----------------------------------------------------------------- gauges
fact_rows         = Gauge("openbi_fact_sales_rows", "Row count in warehouse_big.fact_sales")
monthly_rows      = Gauge("openbi_monthly_revenue_rows", "Row count in warehouse_big.monthly_revenue")
segments_rows     = Gauge("openbi_customer_segments_rows", "Row count in warehouse_big.customer_segments")
forecast_rows     = Gauge("openbi_sales_forecast_rows", "Row count in warehouse_big.sales_forecast")

freshness_seconds = Gauge("openbi_data_freshness_seconds", "Seconds since last pipeline run")

forecast_mape     = Gauge("openbi_forecast_mape", "Winning model's holdout MAPE (%)")

segment_size = Gauge(
    "openbi_segment_size",
    "Customer count per RFM segment",
    labelnames=["label"],
)


# ----------------------------------------------------------------- queries
QUERIES = {
    "fact_rows":     "SELECT COUNT(*) FROM warehouse_big.monthly_revenue",   # placeholder; adjust to your fact table
    "monthly_rows":  "SELECT COUNT(*) FROM warehouse_big.monthly_revenue",
    "segments_rows": "SELECT COUNT(*) FROM warehouse_big.customer_segments",
    "forecast_rows": "SELECT COUNT(*) FROM warehouse_big.sales_forecast",
}


SEGMENT_SQL = """
    SELECT cluster_label, COUNT(*) AS n
    FROM warehouse_big.customer_segments
    GROUP BY cluster_label
"""

FRESHNESS_SQL = """
    SELECT EXTRACT(EPOCH FROM (NOW() - MAX(computed_at)))::int
    FROM warehouse_big.sales_forecast
"""


def refresh() -> None:
    """Query Postgres and update all gauges."""
    engine = get_engine()
    with engine.connect() as conn:
        for name, sql in QUERIES.items():
            try:
                val = conn.execute(text(sql)).scalar() or 0
                globals()[name].set(val)
            except Exception as e:  # noqa: BLE001
                print(f"  [{name}] query failed: {e}")

        try:
            n = conn.execute(text(FRESHNESS_SQL)).scalar()
            if n is not None:
                freshness_seconds.set(n)
        except Exception as e:  # noqa: BLE001
            print(f"  [freshness] query failed: {e}")

        # reset labels then repopulate
        segment_size.clear()
        try:
            for row in conn.execute(text(SEGMENT_SQL)):
                segment_size.labels(label=row[0]).set(row[1])
        except Exception as e:  # noqa: BLE001
            print(f"  [segments] query failed: {e}")


def main() -> None:
    port = int(os.environ.get("EXPORTER_PORT", "9103"))
    interval = int(os.environ.get("EXPORTER_INTERVAL", "30"))

    print(f"▶ OpenBI exporter listening on :{port}")
    start_http_server(port)

    while True:
        try:
            refresh()
        except Exception as e:  # noqa: BLE001
            print(f"  refresh error: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    main()
