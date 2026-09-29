#!/usr/bin/env bash
# Wrapper to spark-submit a job inside the master container.
# Usage: ./spark/run_job.sh jobs/ingest_to_bronze.py [extra args...]

set -euo pipefail

JOB_PATH="${1:?usage: run_job.sh <job-relative-to-spark/> [args...]}"
shift || true

docker exec -it openbi-spark-master \
  /opt/bitnami/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
    --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
    --packages io.delta:delta-spark_2.12:3.1.0 \
    "/opt/openbi/${JOB_PATH}" "$@"
