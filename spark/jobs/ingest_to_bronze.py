"""OpenBI Phase A — ingest raw Parquet into the Bronze Delta layer.

Run locally (inside the spark-master container):
    spark-submit --master spark://spark-master:7077 \
        /opt/openbi/jobs/ingest_to_bronze.py --source parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, current_timestamp, input_file_name, lit
)
from pyspark.sql.types import (
    LongType,
    DateType, DoubleType, IntegerType, StringType, StructField, StructType
)


BRONZE_PATH = "/opt/openbi/data/bronze/sales"
RAW_GLOB = "/opt/openbi/data/raw/big_superstore/*.parquet"


def build_spark(app_name: str = "openbi-bronze-ingest") -> SparkSession:
    builder = (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.extensions",
                "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.shuffle.partitions", "8")
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()


# Explicit schema so ingestion is deterministic
SCHEMA = StructType([
    StructField("row_id",        LongType(),    True),
    StructField("order_id",      StringType(),  True),
    StructField("order_date",    StringType(),  True),
    StructField("ship_date",     StringType(),  True),
    StructField("ship_mode",     StringType(),  True),
    StructField("customer_id",   StringType(),  True),
    StructField("customer_name", StringType(),  True),
    StructField("segment",       StringType(),  True),
    StructField("country",       StringType(),  True),
    StructField("city",          StringType(),  True),
    StructField("state",         StringType(),  True),
    StructField("postal_code",   StringType(),  True),
    StructField("region",        StringType(),  True),
    StructField("product_id",    StringType(),  True),
    StructField("category",      StringType(),  True),
    StructField("sub_category",  StringType(),  True),
    StructField("product_name",  StringType(),  True),
    StructField("sales",         DoubleType(),  True),
    StructField("quantity",      LongType(),    True),
    StructField("discount",      DoubleType(),  True),
    StructField("profit",        DoubleType(),  True),
])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["parquet"], default="parquet")
    ap.add_argument("--raw-glob", default=RAW_GLOB)
    ap.add_argument("--bronze-path", default=BRONZE_PATH)
    ap.add_argument("--mode", choices=["overwrite", "append"], default="overwrite")
    args = ap.parse_args()

    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    print(f"▶ Reading raw Parquet from: {args.raw_glob}")
    raw = (
        spark.read
        .option("mergeSchema", "true")
        # .schema(SCHEMA)  # let Spark infer types from Parquet
        .parquet(args.raw_glob)
    )

    count_before = raw.count()
    print(f"  rows read: {count_before:,}")

    # Add ingestion metadata
    enriched = (
        raw
        .withColumn("_ingested_at", current_timestamp())
        .withColumn("_source_file", input_file_name())
        .withColumn("_layer", lit("bronze"))
    )

    print(f"▶ Writing Delta table: {args.bronze_path} (mode={args.mode})")
    (
        enriched.write
        .format("delta")
        .mode(args.mode)
        .partitionBy("category")
        .save(args.bronze_path)
    )

    # Verify
    written = spark.read.format("delta").load(args.bronze_path)
    count_after = written.count()
    print(f"  rows written: {count_after:,}")

    if count_after != count_before:
        sys.exit(f"ERROR: count mismatch — read {count_before}, wrote {count_after}")

    print("\n▶ Schema:")
    written.printSchema()

    print("\n▶ Sample:")
    written.select(
        "order_id", "order_date", "customer_id",
        "category", "sales", "profit"
    ).show(5, truncate=False)

    print(f"\n✓ Bronze ingestion complete: {count_after:,} rows")
    spark.stop()


if __name__ == "__main__":
    main()
