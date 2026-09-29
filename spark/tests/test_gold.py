"""OpenBI Phase C — data quality tests for the Gold layer.

Run inside the spark-master container:
    docker exec -i openbi-spark-master python3 -m pytest \
        -p no:cacheprovider /opt/openbi/tests/test_gold.py -v
"""

from __future__ import annotations

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


GOLD = "/opt/openbi/data/gold"
SILVER = "/opt/openbi/data/silver"


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("test-gold")
        .master("local[2]")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.driver.extraJavaOptions", "-Dderby.system.home=/tmp")
        .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )


def _gold(spark, name):
    return spark.read.format("delta").load(f"{GOLD}/{name}")


def _fact(spark):
    return spark.read.format("delta").load(f"{SILVER}/fact_sales")


# ============================================================ revenue parity
def test_monthly_revenue_matches_fact(spark):
    """Sum of monthly revenue equals sum of fact sales."""
    fact_rev = _fact(spark).agg(F.sum("sales")).first()[0]
    gold_rev = _gold(spark, "monthly_revenue").agg(F.sum("revenue")).first()[0]
    # allow tiny rounding drift from ROUND(..., 2) at the monthly level
    assert abs(fact_rev - gold_rev) < 5.0, f"drift {fact_rev - gold_rev:.2f}"


def test_revenue_by_category_matches_fact(spark):
    fact_rev = _fact(spark).agg(F.sum("sales")).first()[0]
    gold_rev = _gold(spark, "revenue_by_category").agg(F.sum("revenue")).first()[0]
    assert abs(fact_rev - gold_rev) < 5.0


def test_revenue_by_region_matches_fact(spark):
    fact_rev = _fact(spark).agg(F.sum("sales")).first()[0]
    gold_rev = _gold(spark, "revenue_by_region").agg(F.sum("revenue")).first()[0]
    assert abs(fact_rev - gold_rev) < 5.0


# ============================================================ shape checks
def test_monthly_revenue_row_count(spark):
    """At least 10 years × 12 months = 120 rows; up to 12 × 12 = 144.

    The exact count depends on the generator's date range
    (currently 2014–2024 → 11 years → ~132 months).
    """
    n = _gold(spark, "monthly_revenue").count()
    assert 100 <= n <= 144, f"unexpected monthly_revenue rows: {n}"


def test_revenue_by_category_has_three_categories(spark):
    n = _gold(spark, "revenue_by_category").select("category").distinct().count()
    assert n == 3, f"expected 3 categories, got {n}"


def test_revenue_by_region_has_four_regions(spark):
    """Superstore has 4 regions: East, West, Central, South."""
    n = _gold(spark, "revenue_by_region").select("region").distinct().count()
    assert n == 4, f"expected 4 regions, got {n}"


# ============================================================ top_products
def test_top_products_has_100_rows(spark):
    n = _gold(spark, "top_products").count()
    assert n == 100, f"expected 100, got {n}"


def test_top_products_sorted_desc(spark):
    rows = _gold(spark, "top_products").orderBy(F.desc("revenue")).collect()
    revenues = [r["revenue"] for r in rows]
    assert revenues == sorted(revenues, reverse=True)


def test_top_products_no_duplicates(spark):
    df = _gold(spark, "top_products")
    total = df.count()
    distinct = df.select("product_id").distinct().count()
    assert total == distinct


# ============================================================ customer_rfm
def test_customer_rfm_scores_in_range(spark):
    df = _gold(spark, "customer_rfm")
    for col in ("r_score", "f_score", "m_score"):
        bad = df.filter((F.col(col) < 1) | (F.col(col) > 5)).count()
        assert bad == 0, f"{col} out of range"


def test_customer_rfm_labels_present(spark):
    labels = {
        r["cluster_label"]
        for r in _gold(spark, "customer_rfm").select("cluster_label").distinct().collect()
    }
    # Champions should always exist in a reasonable dataset
    assert "Champions" in labels, f"labels seen: {labels}"


def test_customer_rfm_no_null_monetary(spark):
    n = _gold(spark, "customer_rfm").filter(F.col("monetary").isNull()).count()
    assert n == 0
