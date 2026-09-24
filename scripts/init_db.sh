#!/usr/bin/env bash
set -euo pipefail

echo "▶ Starting Postgres container..."
docker compose up -d postgres

echo "▶ Waiting for Postgres to be healthy..."
until docker exec openbi-postgres pg_isready -U "${POSTGRES_USER:-openbi}" >/dev/null 2>&1; do
  sleep 1
done
echo "✓ Postgres is up."

echo "▶ Running full ETL pipeline..."
python -m openbi.etl.pipeline

echo "✓ Done."
