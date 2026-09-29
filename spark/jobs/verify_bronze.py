"""OpenBI Phase A — verify the Bronze Delta table.

Run:
    ./spark/run_job.sh jobs/verify_bronze.py
"""

from __future__ import annotations

from pyspark.sql import SparkSession
from pyspark.sql.functions import col


BRONZE_PATH = "/opt/openbi/data/bronze/sales"


def build_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("verify-bronze")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )


def main() -> None:
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    df = spark.read.format("delta").load(BRONZE_PATH)

    n = df.count()
    print(f"\n✓ rows: {n:,}\n")

    print("▶ Rows + revenue + profit by category:")
    df.groupBy("category").agg(
        {"sales": "sum", "profit": "sum", "*": "count"}
    ).orderBy("category").show(truncate=False)

    print("▶ Date range:")
    df.selectExpr(
        "min(order_date) as min_date",
        "max(order_date) as max_date",
    ).show(truncate=False)

    print("▶ Sample rows:")
    df.select("order_id", "order_date", "category", "sales", "profit").show(5)

    spark.stop()
    print("✓ verify complete")


if __name__ == "__main__":
    main()
