"""OpenBI — daily ETL DAG."""

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
    dag_id="openbi_etl",
    description="Reload CSV → Postgres warehouse",
    schedule="0 8 * * *",          # daily at 08:00
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["openbi", "etl"],
) as dag:

    load_csv = BashOperator(
        task_id="load_csv",
        bash_command="cd /opt/airflow/openbi_src/.. && python -m openbi.ingestion.load_csv",
    )

    transform = BashOperator(
        task_id="transform",
        bash_command="cd /opt/airflow/openbi_src/.. && python -m openbi.etl.pipeline",
    )

    load_csv >> transform
