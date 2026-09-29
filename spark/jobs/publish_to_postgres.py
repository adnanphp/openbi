"""OpenBI Phase C — Publish Gold Delta tables to Postgres (JDBC).

Writes the 5 gold aggregates into the `warehouse_big` schema in Postgres.
The v1 `warehouse` schema is untouched.

Run:
    ./spark/run_job.sh jobs/publish_to_postgres.py

Target:
    postgresql://openbi:openbi@openbi-postgres:5432/openbi  → schema warehouse_big
"""

from __future__ import annotations

import argparse
import time

from pyspark.sql import SparkSession, DataFrame


GOLD_ROOT = "/opt/openbi/data/gold"

PG_HOST = "openbi-postgres"
PG_PORT = 5432
PG_DB = "openbi"
PG_USER = "openbi"
PG_PASSWORD = "openbi"
PG_SCHEMA = "warehouse_big"

JDBC_URL = f"jdbc:postgresql://{PG_HOST}:{PG_PORT}/{PG_DB}"

# (gold_table_name, target_table_name, sort_column_for_deterministic_order)
TABLES = [
    ("monthly_revenue",     "monthly_revenue",     ["year", "month"]),
    ("revenue_by_category", "revenue_by_category", ["revenue"]),
    ("revenue_by_region",   "revenue_by_region",   ["revenue"]),
    ("top_products",        "top_products",        ["revenue"]),
    ("customer_rfm",        "customer_rfm",        ["monetary"]),
]


def build_spark(app_name: str = "openbi-publish-postgres") -> SparkSession:
    return (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )


def _section(title: str) -> None:
    print(f"\n{'─' * 70}\n▶ {title}\n{'─' * 70}")


def write_table(df: DataFrame, table_name: str, sort_cols: list[str]) -> int:
    """Write df to Postgres, return row count."""
    # Sort for deterministic physical ordering — nice for reading psql output
    try:
        df = df.orderBy(*sort_cols)
    except Exception:
        pass  # if the column doesn't exist, skip

    (
        df.write
          .format("jdbc")
          .option("url", JDBC_URL)
          .option("dbtable", f"{PG_SCHEMA}.{table_name}")
          .option("user", PG_USER)
          .option("password", PG_PASSWORD)
          .option("driver", "org.postgresql.Driver")
          .option("truncate", "true")
          .mode("overwrite")
          .save()
    )
    return df.count()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-root", default=GOLD_ROOT)
    args = ap.parse_args()

    print("=" * 70)
    print("  OpenBI — Publish Gold → Postgres")
    print("=" * 70)
    print(f"  target: {JDBC_URL}  schema={PG_SCHEMA}")

    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    t0 = time.time()
    results = []

    for gold_name, pg_name, sort_cols in TABLES:
        _section(f"{gold_name} → {PG_SCHEMA}.{pg_name}")
        df = spark.read.format("delta").load(f"{args.gold_root}/{gold_name}")
        n = write_table(df, pg_name, sort_cols)
        print(f"  ✓ wrote {n:,} rows")

        # verify immediately
        readback = (
            spark.read.format("jdbc")
            .option("url", JDBC_URL)
            .option("dbtable", f"{PG_SCHEMA}.{pg_name}")
            .option("user", PG_USER)
            .option("password", PG_PASSWORD)
            .option("driver", "org.postgresql.Driver")
            .load()
        )
        n_pg = readback.count()
        if n_pg != n:
            print(f"  ⚠ WARNING: spark={n} postgres={n_pg}")
        else:
            print(f"  ✓ verified {n_pg:,} rows in Postgres")

        results.append((gold_name, n, n_pg))

    _section("Summary")
    print(f"  {'table':25s} {'spark':>10s} {'postgres':>10s}")
    for name, n_spark, n_pg in results:
        flag = "✓" if n_spark == n_pg else "⚠"
        print(f"  {name:25s} {n_spark:>10,} {n_pg:>10,}  {flag}")

    print(f"\n  elapsed: {time.time() - t0:.1f}s")
    spark.stop()
    print("\n✓ Publish complete")


if __name__ == "__main__":
    main()
