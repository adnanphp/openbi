#!/usr/bin/env bash
# OpenBI — run ETL against whatever Postgres is reachable.
# Does NOT start containers. Use `make up` for that.
set -euo pipefail

echo "▶ Running full ETL pipeline..."
python -m openbi.etl.pipeline
echo "✓ Done."
