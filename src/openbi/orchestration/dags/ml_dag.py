"""OpenBI — weekly ML DAG."""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "openbi",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="openbi_ml",
    description="Weekly RFM segmentation + sales forecasting",
    schedule="0 9 * * 0",          # Sundays at 09:00
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["openbi", "ml"],
) as dag:

    rfm = BashOperator(
        task_id="rfm_segmentation",
        bash_command="cd /opt/airflow/openbi_src/.. && python -m openbi.ml.segmentation.rfm_kmeans",
    )

    forecast = BashOperator(
        task_id="sales_forecast",
        bash_command="cd /opt/airflow/openbi_src/.. && python -m openbi.ml.forecasting.run_forecast",
    )

    rfm >> forecast
