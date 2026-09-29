"""OpenBI — daily batch DAG.

Runs the full big data pipeline every day at 06:00 UTC:
    bronze -> silver -> gold -> postgres -> ML publish

Each task shells out to `docker exec openbi-spark-master spark-submit ...`
so we don't need to install Spark inside the Airflow container.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

DEFAULT_ARGS = {
    "owner": "openbi",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "depends_on_past": False,
}

DOCKER = "docker exec openbi-spark-master"


with DAG(
    dag_id="openbi_daily",
    description="Daily big data pipeline: bronze → silver → gold → postgres",
    schedule="0 6 * * *",     # 06:00 UTC daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["openbi", "bigdata", "etl"],
    max_active_runs=1,
) as dag:

    bronze = BashOperator(
        task_id="ingest_to_bronze",
        bash_command=(
            f"{DOCKER} /opt/bitnami/spark/bin/spark-submit "
            "--master spark://spark-master:7077 "
            "--packages io.delta:delta-spark_2.12:3.1.0 "
            "--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension "
            "--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog "
            "/opt/openbi/jobs/ingest_to_bronze.py --source parquet"
        ),
    )

    silver = BashOperator(
        task_id="bronze_to_silver",
        bash_command=(
            f"{DOCKER} /opt/bitnami/spark/bin/spark-submit "
            "--master spark://spark-master:7077 "
            "--packages io.delta:delta-spark_2.12:3.1.0 "
            "--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension "
            "--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog "
            "/opt/openbi/jobs/bronze_to_silver.py"
        ),
    )

    gold = BashOperator(
        task_id="silver_to_gold",
        bash_command=(
            f"{DOCKER} /opt/bitnami/spark/bin/spark-submit "
            "--master spark://spark-master:7077 "
            "--packages io.delta:delta-spark_2.12:3.1.0 "
            "--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension "
            "--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog "
            "/opt/openbi/jobs/silver_to_gold.py"
        ),
    )

    publish = BashOperator(
        task_id="publish_to_postgres",
        bash_command=(
            f"{DOCKER} /opt/bitnami/spark/bin/spark-submit "
            "--master spark://spark-master:7077 "
            "--packages io.delta:delta-spark_2.12:3.1.0,org.postgresql:postgresql:42.7.3 "
            "--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension "
            "--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog "
            "/opt/openbi/jobs/publish_to_postgres.py"
        ),
    )

    bronze >> silver >> gold >> publish
