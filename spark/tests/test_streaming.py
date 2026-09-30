"""OpenBI Phase I — streaming tests.

These run AFTER the streaming pipeline has produced data.
Skip automatically if the Bronze stream table doesn't exist.
"""

from __future__ import annotations

import os

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

BRONZE = os.environ.get(
    "OPENBI_STREAM_BRONZE",
    "/opt/openbi/data/streaming/bronze_orders",
)


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("test-streaming")
        .master("local[2]")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.1.0")
        .config("spark.driver.extraJavaOptions", "-Dderby.system.home=/tmp")
        .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )


def _has_data(spark) -> bool:
    try:
        return spark.read.format("delta").load(BRONZE).limit(1).count() > 0
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not os.path.exists(BRONZE),
    reason=f"Bronze stream not found at {BRONZE}",
)


def test_bronze_has_data(spark):
    if not _has_data(spark):
        pytest.skip("Bronze stream empty")
    n = spark.read.format("delta").load(BRONZE).count()
    assert n > 0


def test_event_id_unique(spark):
    if not _has_data(spark):
        pytest.skip("Bronze stream empty")
    df = spark.read.format("delta").load(BRONZE)
    total = df.count()
    distinct = df.select("event_id").distinct().count()
    assert total == distinct, f"dupes: {total - distinct}"


def test_sales_non_negative(spark):
    if not _has_data(spark):
        pytest.skip("Bronze stream empty")
    bad = (
        spark.read.format("delta").load(BRONZE)
        .filter(F.col("sales") < 0)
        .count()
    )
    assert bad == 0


def test_required_fields_not_null(spark):
    if not _has_data(spark):
        pytest.skip("Bronze stream empty")
    df = spark.read.format("delta").load(BRONZE)
    for col in ("event_id", "order_id", "sales", "category"):
        n = df.filter(F.col(col).isNull()).count()
        assert n == 0, f"{col} has {n} nulls"
