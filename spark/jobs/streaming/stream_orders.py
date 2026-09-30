"""OpenBI Phase I — Structured Streaming: Kafka → Delta Bronze.

Reads JSON order events from Kafka, parses them against a fixed schema,
writes to a Delta table in append mode with exactly-once semantics
(using a checkpoint location).

Run:
    docker exec openbi-spark-master spark-submit \\
      --master spark://spark-master:7077 \\
      --packages io.delta:delta-spark_2.12:3.1.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 \\
      --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \\
      --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \\
      /opt/openbi/jobs/streaming/stream_orders.py
"""

from __future__ import annotations

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType, IntegerType, LongType, StringType, StructField, StructType, TimestampType
)


EVENT_SCHEMA = StructType([
    StructField("event_id",      StringType(),    False),
    StructField("event_time",    StringType(),    False),
    StructField("order_id",      StringType(),    False),
    StructField("customer_id",   StringType(),    True),
    StructField("customer_name", StringType(),    True),
    StructField("segment",       StringType(),    True),
    StructField("category",      StringType(),    True),
    StructField("sub_category",  StringType(),    True),
    StructField("product_id",    StringType(),    True),
    StructField("region",        StringType(),    True),
    StructField("ship_mode",     StringType(),    True),
    StructField("quantity",      LongType(),      True),
    StructField("sales",         DoubleType(),    True),
    StructField("discount",      DoubleType(),    True),
    StructField("profit",        DoubleType(),    True),
])


def build_spark(app_name: str) -> SparkSession:
    return (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", default="kafka:9092")
    ap.add_argument("--topic", default="orders")
    ap.add_argument("--bronze-path", default="/opt/openbi/data/streaming/bronze_orders")
    ap.add_argument("--checkpoint", default="/opt/openbi/data/checkpoints/orders_bronze")
    ap.add_argument("--trigger-seconds", type=int, default=10)
    args = ap.parse_args()

    print("=" * 70)
    print("  OpenBI — Structured Streaming: Kafka → Delta Bronze")
    print("=" * 70)
    print(f"  kafka:       {args.bootstrap}")
    print(f"  topic:       {args.topic}")
    print(f"  bronze:      {args.bronze_path}")
    print(f"  checkpoint:  {args.checkpoint}")
    print(f"  trigger:     every {args.trigger_seconds}s")
    print()

    spark = build_spark("openbi-stream-orders")
    spark.sparkContext.setLogLevel("WARN")

    raw = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", args.bootstrap)
        .option("subscribe", args.topic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )

    parsed = (
        raw.select(
            F.col("value").cast("string").alias("json_str"),
            F.col("timestamp").alias("kafka_ts"),
        )
        .select(
            F.from_json(F.col("json_str"), EVENT_SCHEMA).alias("e"),
            F.col("kafka_ts"),
        )
        .select("e.*", "kafka_ts")
        .withColumn("event_time", F.to_timestamp("event_time"))
        .withColumn("_ingested_at", F.current_timestamp())
    )

    # Basic validation — drop obviously bad rows
    valid = parsed.filter(
        F.col("event_id").isNotNull()
        & F.col("order_id").isNotNull()
        & F.col("sales").isNotNull()
        & (F.col("sales") >= 0)
    )

    query = (
        valid.writeStream
        .format("delta")
        .outputMode("append")
        .option("checkpointLocation", args.checkpoint)
        .option("mergeSchema", "true")
        .partitionBy("category")
        .trigger(processingTime=f"{args.trigger_seconds} seconds")
        .start(args.bronze_path)
    )

    print("✓ Streaming query started — Ctrl+C to stop")
    query.awaitTermination()


if __name__ == "__main__":
    main()
