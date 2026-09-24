"""OpenBI — end-to-end ETL pipeline (Phase 2 scope)."""

from __future__ import annotations

import sys
from pathlib import Path

from openbi.config.settings import settings
from openbi.utils.db import execute_sql_file, ping
from openbi.ingestion import load_csv


SQL_FILES = [
    "01_create_database.sql",
    "02_create_schema.sql",
    "03_load_staging.sql",
    "04_transform_dimensions.sql",
    "05_transform_facts.sql",
    "06_views_kpis.sql",
]


def run() -> None:
    print("=" * 70)
    print("  OpenBI ETL — Phase 2")
    print("=" * 70)

    if not ping():
        sys.exit("ERROR: Postgres not reachable. Run `docker compose up -d` first.")

    print("\n[1/2] Loading CSV → staging.superstore_raw")
    load_csv.main()

    print("\n[2/2] Running SQL transformations")
    for fname in SQL_FILES:
        fpath = settings.sql_dir / fname
        print(f"  → {fname}")
        execute_sql_file(fpath)

    print("\n✓ ETL complete.")


if __name__ == "__main__":
    run()
