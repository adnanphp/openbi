"""OpenBI Phase B — Bronze → Silver star schema.

Reads the Bronze Delta table, builds 5 dimensions + 1 fact table in Delta,
all sharing the same column names as the v1 Postgres warehouse so Phase C
can publish gold aggregates back with zero remapping.

Run:
    ./spark/run_job.sh jobs/bronze_to_silver.py

Outputs (all Delta, all partitioned where noted):
    data/silver/dim_customer/
    data/silver/dim_product/
    data/silver/dim_region/
    data/silver/dim_ship_mode/
    data/silver/dim_date/
    data/silver/fact_sales/         partitioned by year
"""

from __future__ import annotations

import argparse
import sys
import time

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window


BRONZE_PATH = "/opt/openbi/data/bronze/sales"
SILVER_ROOT = "/opt/openbi/data/silver"


def build_spark(app_name: str = "openbi-silver-build") -> SparkSession:
    return (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def _write_delta(df: DataFrame, path: str, partition_by: list[str] | None = None) -> None:
    writer = df.write.format("delta").mode("overwrite")
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    writer.save(path)


def _section(title: str) -> None:
    print(f"\n{'─' * 70}\n▶ {title}\n{'─' * 70}")


# ============================================================ dim_customer
def build_dim_customer(bronze: DataFrame) -> DataFrame:
    """One row per customer_id, surrogate key via row_number over sorted id."""
    distinct = (
        bronze
        .select("customer_id", "customer_name", "segment")
        .filter(F.col("customer_id").isNotNull())
        .dropDuplicates(["customer_id"])
        .repartition(4)     # parallelize the window
    )
    w = Window.orderBy("customer_id")
    return (
        distinct
        .withColumn("customer_key", F.row_number().over(w))
        .select("customer_key", "customer_id", "customer_name", "segment")
    )


# ============================================================= dim_product
def build_dim_product(bronze: DataFrame) -> DataFrame:
    distinct = (
        bronze
        .select("product_id", "product_name", "category", "sub_category")
        .filter(F.col("product_id").isNotNull())
        .dropDuplicates(["product_id"])
        .repartition(4)
    )
    w = Window.orderBy("product_id")
    return (
        distinct
        .withColumn("product_key", F.row_number().over(w))
        .select("product_key", "product_id", "product_name", "category", "sub_category")
    )


# ============================================================== dim_region
def build_dim_region(bronze: DataFrame) -> DataFrame:
    distinct = (
        bronze
        .select("country", "region", "state", "city", "postal_code")
        .dropDuplicates(["country", "region", "state", "city", "postal_code"])
        .repartition(4)
    )
    w = Window.orderBy("country", "region", "state", "city", "postal_code")
    return (
        distinct
        .withColumn("region_key", F.row_number().over(w))
        .select("region_key", "country", "region", "state", "city", "postal_code")
    )


# =========================================================== dim_ship_mode
def build_dim_ship_mode(bronze: DataFrame) -> DataFrame:
    distinct = (
        bronze
        .select("ship_mode")
        .filter(F.col("ship_mode").isNotNull())
        .dropDuplicates()
        .repartition(4)
    )
    w = Window.orderBy("ship_mode")
    return (
        distinct
        .withColumn("ship_mode_key", F.row_number().over(w))
        .select("ship_mode_key", "ship_mode")
    )


# ============================================================== dim_date
def build_dim_date(bronze: DataFrame) -> DataFrame:
    """One row per calendar day from min(order_date) to max(order_date)."""
    bounds = bronze.select(
        F.to_date(F.min("order_date")).alias("min_d"),
        F.to_date(F.max("order_date")).alias("max_d"),
    ).first()

    min_d, max_d = bounds["min_d"], bounds["max_d"]

    if min_d is None or max_d is None:
        raise ValueError(
            f"Bronze has no valid order_date values. "
            f"min={min_d}, max={max_d}. Check that order_date is a string column "
            f"in ISO format (YYYY-MM-DD)."
        )

    days = (
        bronze.sparkSession
        .range(0, (max_d - min_d).days + 1)
        .select(F.date_add(F.lit(min_d), F.col("id").cast("int")).alias("full_date"))
    )

    return (
        days
        .withColumn("date_key", F.date_format("full_date", "yyyyMMdd").cast("int"))
        .withColumn("year", F.year("full_date"))
        .withColumn("quarter", F.quarter("full_date"))
        .withColumn("month", F.month("full_date"))
        .withColumn("month_name", F.date_format("full_date", "MMM"))
        .withColumn("week", F.weekofyear("full_date"))
        .withColumn("day_of_week", F.dayofweek("full_date"))
        .withColumn("day_name", F.date_format("full_date", "EEE"))
        .withColumn("is_weekend", F.dayofweek("full_date").isin(1, 7))
        .select(
            "date_key", "full_date", "year", "quarter", "month",
            "month_name", "week", "day_of_week", "day_name", "is_weekend",
        )
    )


# ============================================================= fact_sales
def build_fact_sales(
    bronze: DataFrame,
    dim_customer: DataFrame,
    dim_product: DataFrame,
    dim_region: DataFrame,
    dim_ship_mode: DataFrame,
    dim_date: DataFrame,
) -> DataFrame:
    """Join Bronze to all dims, project surrogate keys, partition by year."""
    fact = (
        bronze.alias("b")
        .join(dim_customer.alias("c"), on="customer_id", how="inner")
        .join(dim_product.alias("p"), on="product_id", how="inner")
        .join(
            dim_region.alias("r"),
            on=["country", "region", "state", "city", "postal_code"],
            how="inner",
        )
        .join(dim_ship_mode.alias("sm"), on="ship_mode", how="inner")
        # order_date → order_date_key
        .join(
            dim_date.alias("od"),
            F.to_date(F.col("b.order_date")) == F.col("od.full_date"),
            how="inner",
        )
        .select(
            F.col("b.order_id").alias("order_id"),
            F.col("b.row_id").alias("row_id"),
            F.col("c.customer_key").alias("customer_key"),
            F.col("p.product_key").alias("product_key"),
            F.col("r.region_key").alias("region_key"),
            F.col("sm.ship_mode_key").alias("ship_mode_key"),
            F.col("od.date_key").alias("order_date_key"),
            F.to_date(F.col("b.ship_date")).alias("_ship_date"),  # temp, joined below
            F.col("b.sales").alias("sales"),
            F.col("b.quantity").alias("quantity"),
            F.col("b.discount").alias("discount"),
            F.col("b.profit").alias("profit"),
        )
    )

    # Resolve ship_date_key (left join — may be null)
    fact_with_ship = (
        fact.alias("f")
        .join(
            dim_date.alias("sd"),
            F.col("f._ship_date") == F.col("sd.full_date"),
            how="left",
        )
        .select(
            "f.order_id", "f.row_id",
            "f.customer_key", "f.product_key", "f.region_key",
            "f.ship_mode_key", "f.order_date_key",
            F.col("sd.date_key").alias("ship_date_key"),
            "f.sales", "f.quantity", "f.discount", "f.profit",
            F.year(F.col("f._ship_date")).alias("year"),
        )
    )

    return fact_with_ship


# ============================================================= orchestration
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bronze-path", default=BRONZE_PATH)
    ap.add_argument("--silver-root", default=SILVER_ROOT)
    args = ap.parse_args()

    print("=" * 70)
    print("  OpenBI — Bronze → Silver Star Schema")
    print("=" * 70)

    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    _section("Read Bronze")
    bronze = spark.read.format("delta").load(args.bronze_path)
    n_bronze = bronze.count()
    print(f"  rows: {n_bronze:,}")

    t0 = time.time()

    # ---------------- dims ----------------
    _section("Build dim_customer")
    dim_customer = build_dim_customer(bronze).cache()
    n_cust = dim_customer.count()
    print(f"  rows: {n_cust:,}")
    _write_delta(dim_customer, f"{args.silver_root}/dim_customer")

    _section("Build dim_product")
    dim_product = build_dim_product(bronze).cache()
    n_prod = dim_product.count()
    print(f"  rows: {n_prod:,}")
    _write_delta(dim_product, f"{args.silver_root}/dim_product")

    _section("Build dim_region")
    dim_region = build_dim_region(bronze).cache()
    n_reg = dim_region.count()
    print(f"  rows: {n_reg:,}")
    _write_delta(dim_region, f"{args.silver_root}/dim_region")

    _section("Build dim_ship_mode")
    dim_ship = build_dim_ship_mode(bronze).cache()
    n_ship = dim_ship.count()
    print(f"  rows: {n_ship:,}")
    _write_delta(dim_ship, f"{args.silver_root}/dim_ship_mode")

    _section("Build dim_date")
    dim_date = build_dim_date(bronze).cache()
    n_date = dim_date.count()
    print(f"  rows: {n_date:,}")
    _write_delta(dim_date, f"{args.silver_root}/dim_date")

    # ---------------- fact ----------------
    _section("Build fact_sales")
    fact = build_fact_sales(
        bronze, dim_customer, dim_product, dim_region, dim_ship, dim_date
    )
    n_fact = fact.count()
    print(f"  rows: {n_fact:,}")

    _write_delta(fact, f"{args.silver_root}/fact_sales", partition_by=["year"])

    # ---------------- verify ----------------
    _section("Verification")
    fact_read = spark.read.format("delta").load(f"{args.silver_root}/fact_sales")
    n_fact_after = fact_read.count()
    rev_before = bronze.select(F.sum("sales")).first()[0]
    rev_after = fact_read.select(F.sum("sales")).first()[0]

    print(f"  bronze rows      : {n_bronze:,}")
    print(f"  fact rows        : {n_fact_after:,}")
    print(f"  bronze revenue   : {rev_before:,.2f}")
    print(f"  fact revenue     : {rev_after:,.2f}")

    if n_fact_after != n_bronze:
        print(f"  ⚠ WARNING: fact rows != bronze rows ({n_fact_after} vs {n_bronze})")
    if abs(rev_before - rev_after) > 0.01:
        print(f"  ⚠ WARNING: revenue mismatch (Δ = {rev_before - rev_after:,.2f})")
    else:
        print(f"  ✓ row count and revenue preserved")

    print(f"\n  elapsed: {time.time() - t0:.1f}s")

    spark.stop()
    print("\n✓ Silver star schema complete")


if __name__ == "__main__":
    main()
