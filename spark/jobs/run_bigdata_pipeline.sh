#!/usr/bin/env bash
# OpenBI v2 — end-to-end big data pipeline
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  OpenBI — Big Data Pipeline                                      ║"
echo "╚══════════════════════════════════════════════════════════════════╝"

echo ""
echo "▶ [1/4] Bronze ingestion"
./spark/run_job.sh jobs/ingest_to_bronze.py --source parquet

echo ""
echo "▶ [2/4] Silver star schema"
./spark/run_job.sh jobs/bronze_to_silver.py

echo ""
echo "▶ [3/4] Gold aggregations"
./spark/run_job.sh jobs/silver_to_gold.py

echo ""
echo "▶ [4/4] Publish to Postgres"
./spark/run_job.sh jobs/publish_to_postgres.py

echo ""
echo "✓ Big data pipeline complete"
