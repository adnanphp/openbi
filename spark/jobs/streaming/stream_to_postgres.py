"""OpenBI Phase I — Structured Streaming: Delta Bronze → Postgres.

Reads new rows from the Bronze Delta table and appends them to
warehouse_big.orders_realtime via JDBC. Uses Delta's StreamingSource
so only new rows are picked up per micro-batch.
"""

from __future__ import annotations

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


PG_HOST = "openbi-postgres"
PG_PORT = 5432
PG_DB = "openbi"
PG_USER = "openbi"
PG_PASSWORD = "openbi"

JDBC_URL = f"jdbc:postgresql://{PG_HOST}:{PG_PORT}/{PG_DB}"


def build_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("openbi-stream-to-postgres")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )


def write_batch(batch_df, batch_id: int) -> None:
    n = batch_df.count()
    if n == 0:
        return
    print(f"  batch {batch_id}: writing {n:,} rows to Postgres")
    (
        batch_df.select(
            "event_id", "event_time", "order_id",
            "customer_id", "customer_name", "segment",
            "category", "sub_category", "product_id",
            "region", "ship_mode",
            "quantity", "sales", "discount", "profit",
        )
        .write
        .format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", "warehouse_big.orders_realtime")
        .option("user", PG_USER)
        .option("password", PG_PASSWORD)
        .option("driver", "org.postgresql.Driver")
        .mode("append")
        .save()
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bronze-path", default="/opt/openbi/data/streaming/bronze_orders")
    ap.add_argument("--checkpoint", default="/opt/openbi/data/checkpoints/orders_postgres")
    ap.add_argument("--trigger-seconds", type=int, default=10)
    args = ap.parse_args()

    print("=" * 70)
    print("  OpenBI — Structured Streaming: Delta → Postgres")
    print("=" * 70)
    print(f"  bronze:     {args.bronze_path}")
    print(f"  target:     {JDBC_URL}  table=warehouse_big.orders_realtime")
    print()

    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    stream = (
        spark.readStream
        .format("delta")
        .option("ignoreDeletes", "true")
        .load(args.bronze_path)
    )

    query = (
        stream.writeStream
        .foreachBatch(write_batch)
        .outputMode("append")
        .option("checkpointLocation", args.checkpoint)
        .trigger(processingTime=f"{args.trigger_seconds} seconds")
        .start()
    )

    print("✓ Streaming query started — Ctrl+C to stop")
    query.awaitTermination()


if __name__ == "__main__":
    main()
