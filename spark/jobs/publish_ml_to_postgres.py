"""OpenBI Phase D — publish ML gold tables to Postgres.

Writes data/gold/customer_segments and data/gold/sales_forecast into
the warehouse_big schema via JDBC.

Run:
    ./spark/run_job.sh jobs/publish_ml_to_postgres.py
"""

from __future__ import annotations

import argparse
import time

from pyspark.sql import SparkSession, DataFrame


GOLD_ROOT = "/opt/openbi/data/gold"

JDBC_URL = "jdbc:postgresql://openbi-postgres:5432/openbi"
PG_USER = "openbi"
PG_PASSWORD = "openbi"
PG_SCHEMA = "warehouse_big"

TABLES = [
    ("customer_segments", "customer_segments", ["monetary"]),
    ("sales_forecast",    "sales_forecast",    ["forecast_month"]),
]


def build_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("openbi-publish-ml")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )


def _section(title: str) -> None:
    print(f"\n{'─' * 70}\n▶ {title}\n{'─' * 70}")


def write_table(df: DataFrame, table_name: str, sort_cols: list[str]) -> int:
    try:
        df = df.orderBy(*sort_cols)
    except Exception:
        pass
    (df.write
       .format("jdbc")
       .option("url", JDBC_URL)
       .option("dbtable", f"{PG_SCHEMA}.{table_name}")
       .option("user", PG_USER)
       .option("password", PG_PASSWORD)
       .option("driver", "org.postgresql.Driver")
       .option("truncate", "true")
       .mode("overwrite")
       .save())
    return df.count()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-root", default=GOLD_ROOT)
    args = ap.parse_args()

    print("=" * 70)
    print("  OpenBI — Publish ML Gold → Postgres")
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
        flag = "✓" if n_pg == n else "⚠"
        print(f"  {flag} verified {n_pg:,} rows in Postgres")
        results.append((gold_name, n, n_pg))

    _section("Summary")
    print(f"  {'table':25s} {'spark':>10s} {'postgres':>10s}")
    for name, n_spark, n_pg in results:
        flag = "✓" if n_spark == n_pg else "⚠"
        print(f"  {name:25s} {n_spark:>10,} {n_pg:>10,}  {flag}")

    print(f"\n  elapsed: {time.time() - t0:.1f}s")
    spark.stop()
    print("\n✓ ML publish complete")


if __name__ == "__main__":
    main()
