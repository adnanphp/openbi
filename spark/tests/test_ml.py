"""OpenBI Phase D — data quality tests for the ML outputs."""

from __future__ import annotations

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


GOLD = "/opt/openbi/data/gold"


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("test-ml")
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


# ---------------------------------------------------------- customer_segments
def test_segments_row_count(spark):
    n = _gold(spark, "customer_segments").count()
    assert n > 100, f"too few customers: {n}"


def test_segments_scores_in_range(spark):
    df = _gold(spark, "customer_segments")
    for col in ("r_score", "f_score", "m_score"):
        bad = df.filter((F.col(col) < 1) | (F.col(col) > 5)).count()
        assert bad == 0, f"{col} out of range"


def test_segments_labels_present(spark):
    labels = {
        r["cluster_label"]
        for r in _gold(spark, "customer_segments").select("cluster_label").distinct().collect()
    }
    assert "Champions" in labels, f"labels: {labels}"
    assert len(labels) >= 3


def test_segments_no_null_monetary(spark):
    n = _gold(spark, "customer_segments").filter(F.col("monetary").isNull()).count()
    assert n == 0


def test_segments_customer_id_unique(spark):
    df = _gold(spark, "customer_segments")
    total = df.count()
    distinct = df.select("customer_id").distinct().count()
    assert total == distinct


# ------------------------------------------------------------ sales_forecast
def test_forecast_row_count(spark):
    """6 months × 3 models = 18 rows."""
    n = _gold(spark, "sales_forecast").count()
    assert n == 18, f"expected 18, got {n}"


def test_forecast_exactly_one_winner_per_month(spark):
    df = _gold(spark, "sales_forecast").filter(F.col("is_winner"))
    n = df.count()
    assert n == 6, f"expected 6 winner rows, got {n}"
    n_months = df.select("forecast_month").distinct().count()
    assert n_months == 6


def test_forecast_yhat_positive(spark):
    n = _gold(spark, "sales_forecast").filter(F.col("yhat") <= 0).count()
    assert n == 0


def test_forecast_three_models(spark):
    models = {
        r["model_name"]
        for r in _gold(spark, "sales_forecast").select("model_name").distinct().collect()
    }
    assert models == {"baseline_ma", "ets", "xgboost"}
