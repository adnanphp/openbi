"""OpenBI — hourly data freshness checks."""
from __future__ import annotations
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

DEFAULT_ARGS = {"owner": "openbi", "retries": 0, "email_on_failure": False}
PSQL = "docker exec openbi-postgres psql -U openbi -d openbi -tAc"

with DAG(
    dag_id="openbi_smoke",
    description="Hourly health checks for warehouse_big",
    schedule="0 * * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["openbi", "bigdata", "monitoring"],
) as dag:

    check_monthly = BashOperator(
        task_id="check_monthly_revenue",
        bash_command=(
            f'rows=$({PSQL} "SELECT COUNT(*) FROM warehouse_big.monthly_revenue"); '
            f'echo "monthly_revenue rows: $rows"; '
            f'[ "$rows" -gt 100 ] || (echo "too few rows" && exit 1)'
        ),
    )
    check_segments = BashOperator(
        task_id="check_customer_segments",
        bash_command=(
            f'rows=$({PSQL} "SELECT COUNT(*) FROM warehouse_big.customer_segments"); '
            f'echo "customer_segments rows: $rows"; '
            f'[ "$rows" -gt 100 ] || (echo "too few rows" && exit 1)'
        ),
    )
    check_forecast = BashOperator(
        task_id="check_sales_forecast",
        bash_command=(
            f'rows=$({PSQL} "SELECT COUNT(*) FROM warehouse_big.sales_forecast"); '
            f'echo "sales_forecast rows: $rows"; '
            f'[ "$rows" -gt 5 ] || (echo "too few rows" && exit 1)'
        ),
    )

    check_monthly >> check_segments >> check_forecast
