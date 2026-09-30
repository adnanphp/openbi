"""OpenBI — weekly ML DAG."""
from __future__ import annotations
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

DEFAULT_ARGS = {
    "owner": "openbi", "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}
DOCKER = "docker exec openbi-spark-master"
PKGS = "io.delta:delta-spark_2.12:3.1.0,org.postgresql:postgresql:42.7.3"
SPARK_SUBMIT = (
    f"{DOCKER} /opt/bitnami/spark/bin/spark-submit "
    "--master spark://spark-master:7077 "
    f"--packages {PKGS} "
    "--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension "
    "--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog"
)

with DAG(
    dag_id="openbi_ml",
    description="Weekly RFM + KMeans + forecasting",
    schedule="0 7 * * 0",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["openbi", "bigdata", "ml"],
    max_active_runs=1,
) as dag:

    rfm        = BashOperator(task_id="rfm_kmeans",
                              bash_command=f"{SPARK_SUBMIT} /opt/openbi/jobs/ml_rfm_kmeans.py")
    forecast   = BashOperator(task_id="forecast",
                              bash_command=f"{SPARK_SUBMIT} /opt/openbi/jobs/ml_forecast.py")
    publish_ml = BashOperator(task_id="publish_ml",
                              bash_command=f"{SPARK_SUBMIT} /opt/openbi/jobs/publish_ml_to_postgres.py")

    rfm >> forecast >> publish_ml
