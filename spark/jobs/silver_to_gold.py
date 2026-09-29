"""OpenBI Phase C — Silver → Gold aggregations.

Reads the Silver star schema, produces small pre-aggregated Delta tables
that mirror the v1 Postgres KPI views. These are what get published to
Postgres (warehouse_big schema) in publish_to_postgres.py.

Run:
    ./spark/run_job.sh jobs/silver_to_gold.py

Outputs:
    data/gold/monthly_revenue/       (Delta)
    data/gold/revenue_by_category/   (Delta)
    data/gold/revenue_by_region/     (Delta)
    data/gold/top_products/          (Delta)
    data/gold/customer_rfm/          (Delta)
"""

from __future__ import annotations

import argparse
import time

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window


SILVER_ROOT = "/opt/openbi/data/silver"
GOLD_ROOT = "/opt/openbi/data/gold"


def build_spark(app_name: str = "openbi-gold-build") -> SparkSession:
    return (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def _read(spark, name: str) -> DataFrame:
    return spark.read.format("delta").load(f"{SILVER_ROOT}/{name}")


def _write(df: DataFrame, name: str, gold_root: str) -> None:
    (df.write
       .format("delta")
       .mode("overwrite")
       .save(f"{gold_root}/{name}"))


def _section(title: str) -> None:
    print(f"\n{'─' * 70}\n▶ {title}\n{'─' * 70}")


# ============================================================ monthly_revenue
def build_monthly_revenue(fact: DataFrame, dim_date: DataFrame) -> DataFrame:
    # fact.year is the partition column; dim_date.year is the calendar year.
    # Drop fact.year before the join to avoid ambiguity.
    fact_clean = fact.drop("year")
    return (
        fact_clean.join(dim_date, fact_clean.order_date_key == dim_date.date_key, "inner")
        .groupBy(dim_date.year, dim_date.month, dim_date.month_name)
        .agg(
            F.round(F.sum("sales"), 2).alias("revenue"),
            F.round(F.sum("profit"), 2).alias("profit"),
            F.countDistinct("order_id").alias("orders"),
            F.round(F.avg("sales"), 2).alias("avg_line_value"),
        )
        .orderBy("year", "month")
    )


# ======================================================== revenue_by_category
def build_revenue_by_category(fact: DataFrame, dim_product: DataFrame) -> DataFrame:
    return (
        fact.join(dim_product, on="product_key", how="inner")
        .groupBy("category", "sub_category")
        .agg(
            F.round(F.sum("sales"), 2).alias("revenue"),
            F.round(F.sum("profit"), 2).alias("profit"),
            F.sum("quantity").alias("units"),
        )
        .orderBy(F.desc("revenue"))
    )


# =========================================================== revenue_by_region
def build_revenue_by_region(fact: DataFrame, dim_region: DataFrame) -> DataFrame:
    return (
        fact.join(dim_region, on="region_key", how="inner")
        .groupBy("region", "state")
        .agg(
            F.round(F.sum("sales"), 2).alias("revenue"),
            F.round(F.sum("profit"), 2).alias("profit"),
        )
        .orderBy(F.desc("revenue"))
    )


# =============================================================== top_products
def build_top_products(fact: DataFrame, dim_product: DataFrame, limit: int = 100) -> DataFrame:
    agg = (
        fact.join(dim_product, on="product_key", how="inner")
        .groupBy("product_id", "product_name", "category")
        .agg(
            F.round(F.sum("sales"), 2).alias("revenue"),
            F.round(F.sum("profit"), 2).alias("profit"),
            F.sum("quantity").alias("units"),
        )
    )
    # deterministic ranking — tie-break by product_id for reproducibility
    w = Window.orderBy(F.desc("revenue"), F.asc("product_id"))
    return (
        agg.withColumn("_rank", F.row_number().over(w))
           .filter(F.col("_rank") <= limit)
           .drop("_rank")
           .orderBy(F.desc("revenue"))
    )


# ============================================================== customer_rfm
def build_customer_rfm(fact: DataFrame, dim_customer: DataFrame, dim_date: DataFrame) -> DataFrame:
    # Anchor recency to the last order date in the data (not CURRENT_DATE)
    snapshot = dim_date.agg(F.max("full_date").alias("snap")).first()["snap"]

    base = (
        fact.drop("year")     # avoid collision with dim_date.year
        .join(dim_customer, on="customer_key", how="inner")
        .join(dim_date, fact.order_date_key == dim_date.date_key, "inner")
        .groupBy("customer_id", "customer_name", "segment")
        .agg(
            F.datediff(F.lit(snapshot), F.max("full_date")).alias("recency_days"),
            F.countDistinct("order_id").alias("frequency"),
            F.round(F.sum("sales"), 2).alias("monetary"),
        )
    )

    # Quintile scores 1..5 (5 = best)
    w_r = Window.orderBy(F.asc("recency_days"))   # smaller recency = better
    w_f = Window.orderBy(F.asc("frequency"))
    w_m = Window.orderBy(F.asc("monetary"))

    total = base.count()
    # ntile(5) gives 1..5 in the order specified; invert for recency
    scored = (
        base
        .withColumn("_r_ntile", F.ntile(5).over(w_r))
        .withColumn("_f_ntile", F.ntile(5).over(w_f))
        .withColumn("_m_ntile", F.ntile(5).over(w_m))
        .withColumn("r_score", (6 - F.col("_r_ntile")).cast("int"))  # invert
        .withColumn("f_score", F.col("_f_ntile").cast("int"))
        .withColumn("m_score", F.col("_m_ntile").cast("int"))
        .drop("_r_ntile", "_f_ntile", "_m_ntile")
    )

    scored = scored.withColumn(
        "rfm_score",
        F.concat(F.col("r_score"), F.col("f_score"), F.col("m_score")),
    )

    # Rule-based labels (same rules as v1 rfm_kmeans.py)
    label = (
        F.when((F.col("r_score") >= 4) & (F.col("f_score") >= 4) & (F.col("m_score") >= 4), "Champions")
         .when((F.col("r_score") >= 3) & (F.col("f_score") >= 4) & (F.col("m_score") >= 3), "Loyal Customers")
         .when((F.col("r_score") >= 4) & (F.col("f_score") >= 2) & (F.col("m_score") >= 2), "Potential Loyalists")
         .when((F.col("r_score") <= 2) & (F.col("f_score") >= 3) & (F.col("m_score") >= 3), "At Risk")
         .when((F.col("r_score") <= 2) & (F.col("f_score") <= 2) & (F.col("m_score") <= 2), "Lost")
         .when((F.col("r_score") >= 4) & (F.col("f_score") == 1), "New Customers")
         .otherwise("Need Attention")
    )

    return (
        scored
        .withColumn("cluster_label", label)
        .select(
            "customer_id", "customer_name", "segment",
            "recency_days", "frequency", "monetary",
            "r_score", "f_score", "m_score", "rfm_score", "cluster_label",
        )
    )


# ============================================================= orchestration
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--silver-root", default=SILVER_ROOT)
    ap.add_argument("--gold-root", default=GOLD_ROOT)
    ap.add_argument("--top-n", type=int, default=100)
    args = ap.parse_args()

    print("=" * 70)
    print("  OpenBI — Silver → Gold Aggregations")
    print("=" * 70)

    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    t0 = time.time()

    _section("Read Silver")
    fact = spark.read.format("delta").load(f"{args.silver_root}/fact_sales").cache()
    dim_customer = spark.read.format("delta").load(f"{args.silver_root}/dim_customer").cache()
    dim_product = spark.read.format("delta").load(f"{args.silver_root}/dim_product").cache()
    dim_region = spark.read.format("delta").load(f"{args.silver_root}/dim_region").cache()
    dim_date = spark.read.format("delta").load(f"{args.silver_root}/dim_date").cache()
    print(f"  fact rows: {fact.count():,}")

    _section("Build monthly_revenue")
    monthly = build_monthly_revenue(fact, dim_date)
    print(f"  rows: {monthly.count():,}")
    _write(monthly, "monthly_revenue", args.gold_root)

    _section("Build revenue_by_category")
    by_cat = build_revenue_by_category(fact, dim_product)
    print(f"  rows: {by_cat.count():,}")
    _write(by_cat, "revenue_by_category", args.gold_root)

    _section("Build revenue_by_region")
    by_reg = build_revenue_by_region(fact, dim_region)
    print(f"  rows: {by_reg.count():,}")
    _write(by_reg, "revenue_by_region", args.gold_root)

    _section(f"Build top_products (top {args.top_n})")
    top = build_top_products(fact, dim_product, limit=args.top_n)
    print(f"  rows: {top.count():,}")
    _write(top, "top_products", args.gold_root)

    _section("Build customer_rfm")
    rfm = build_customer_rfm(fact, dim_customer, dim_date)
    print(f"  rows: {rfm.count():,}")
    _write(rfm, "customer_rfm", args.gold_root)

    _section("Verification — Gold totals match fact")
    fact_rev = fact.agg(F.sum("sales")).first()[0]
    gold_rev = monthly.agg(F.sum("revenue")).first()[0]
    print(f"  fact revenue : {fact_rev:,.2f}")
    print(f"  gold revenue : {gold_rev:,.2f}")
    if abs(fact_rev - gold_rev) > 1.0:
        print(f"  ⚠ WARNING: revenue drift = {fact_rev - gold_rev:,.2f}")
    else:
        print("  ✓ revenue preserved")

    print(f"\n  elapsed: {time.time() - t0:.1f}s")

    spark.stop()
    print("\n✓ Gold aggregations complete")


if __name__ == "__main__":
    main()
