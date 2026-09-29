"""OpenBI Phase B — data quality tests for the Silver layer.

Run inside the spark-master container:
    docker exec -i openbi-spark-master python3 -m pytest /opt/openbi/tests/test_silver.py -v
"""

from __future__ import annotations

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


SILVER = "/opt/openbi/data/silver"
BRONZE = "/opt/openbi/data/bronze/sales"


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("test-silver")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.1.0")
        .getOrCreate()
    )


def _read(spark, name):
    return spark.read.format("delta").load(f"{SILVER}/{name}")


# ---------------------------------------------------------- row counts
def test_fact_row_count_matches_bronze(spark):
    bronze = spark.read.format("delta").load(BRONZE).count()
    fact = _read(spark, "fact_sales").count()
    assert fact == bronze, f"fact={fact} bronze={bronze}"


def test_revenue_preserved(spark):
    bronze_rev = (
        spark.read.format("delta").load(BRONZE)
        .agg(F.sum("sales")).first()[0]
    )
    fact_rev = _read(spark, "fact_sales").agg(F.sum("sales")).first()[0]
    assert abs(bronze_rev - fact_rev) < 0.01


def test_profit_preserved(spark):
    bronze_profit = (
        spark.read.format("delta").load(BRONZE)
        .agg(F.sum("profit")).first()[0]
    )
    fact_profit = _read(spark, "fact_sales").agg(F.sum("profit")).first()[0]
    assert abs(bronze_profit - fact_profit) < 0.01


# ---------------------------------------------------------- uniqueness
def test_dim_customer_key_unique(spark):
    df = _read(spark, "dim_customer")
    total = df.count()
    distinct = df.select("customer_key").distinct().count()
    assert total == distinct


def test_dim_customer_id_unique(spark):
    df = _read(spark, "dim_customer")
    total = df.count()
    distinct = df.select("customer_id").distinct().count()
    assert total == distinct


def test_dim_product_key_unique(spark):
    df = _read(spark, "dim_product")
    total = df.count()
    distinct = df.select("product_key").distinct().count()
    assert total == distinct


def test_dim_date_key_unique(spark):
    df = _read(spark, "dim_date")
    total = df.count()
    distinct = df.select("date_key").distinct().count()
    assert total == distinct


# ---------------------------------------------------------- null checks
def test_fact_foreign_keys_not_null(spark):
    df = _read(spark, "fact_sales")
    for col in ("customer_key", "product_key", "region_key",
                "ship_mode_key", "order_date_key"):
        nulls = df.filter(F.col(col).isNull()).count()
        assert nulls == 0, f"{col} has {nulls} nulls"


def test_fact_measures_not_null(spark):
    df = _read(spark, "fact_sales")
    for col in ("sales", "quantity", "discount", "profit"):
        nulls = df.filter(F.col(col).isNull()).count()
        assert nulls == 0, f"{col} has {nulls} nulls"


# ------------------------------------------------- referential integrity
def test_fact_customer_key_in_dim(spark):
    fact = _read(spark, "fact_sales").select("customer_key").distinct()
    dim = _read(spark, "dim_customer").select("customer_key").distinct()
    orphans = fact.subtract(dim).count()
    assert orphans == 0


def test_fact_product_key_in_dim(spark):
    fact = _read(spark, "fact_sales").select("product_key").distinct()
    dim = _read(spark, "dim_product").select("product_key").distinct()
    orphans = fact.subtract(dim).count()
    assert orphans == 0


# ---------------------------------------------------------- dim_date logic
def test_dim_date_weekend_flag(spark):
    df = _read(spark, "dim_date")
    # Spark DOW: 1=Sunday, 7=Saturday
    assert df.filter(
        (F.col("day_of_week").isin(1, 7)) & (~F.col("is_weekend"))
    ).count() == 0
    assert df.filter(
        (~F.col("day_of_week").isin(1, 7)) & F.col("is_weekend")
    ).count() == 0


def test_dim_date_continuous(spark):
    """No gaps in the calendar."""
    df = _read(spark, "dim_date").orderBy("full_date")
    min_d, max_d = df.select(F.min("full_date"), F.max("full_date")).first()
    expected_days = (max_d - min_d).days + 1
    actual_days = df.count()
    assert actual_days == expected_days
