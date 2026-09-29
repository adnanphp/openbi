"""OpenBI Phase D — RFM segmentation with Spark MLlib KMeans.

Reads Silver fact + dims, computes RFM per customer, scores 1..5 by quintile,
clusters via Spark MLlib KMeans, labels clusters via rule-based mapping,
writes to data/gold/customer_segments/.

Run:
    ./spark/run_job.sh jobs/ml_rfm_kmeans.py
"""

from __future__ import annotations

import argparse
import time

from pyspark.ml.clustering import KMeans
from pyspark.ml.feature import StandardScaler, VectorAssembler
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window


SILVER_ROOT = "/opt/openbi/data/silver"
GOLD_ROOT = "/opt/openbi/data/gold"


def build_spark(app_name: str = "openbi-ml-rfm") -> SparkSession:
    return (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def _section(title: str) -> None:
    print(f"\n{'─' * 70}\n▶ {title}\n{'─' * 70}")


# ============================================================== RFM compute
def compute_rfm(fact: DataFrame, dim_customer: DataFrame, dim_date: DataFrame) -> DataFrame:
    """Recency anchored to the max order date in the data."""
    snapshot = dim_date.agg(F.max("full_date").alias("snap")).first()["snap"]
    print(f"  snapshot date: {snapshot}")

    fact_clean = fact.drop("year")     # avoid collision with dim_date.year
    return (
        fact_clean
        .join(dim_customer, on="customer_key", how="inner")
        .join(dim_date, fact_clean.order_date_key == dim_date.date_key, "inner")
        .groupBy("customer_id", "customer_name", "segment")
        .agg(
            F.datediff(F.lit(snapshot), F.max("full_date")).alias("recency_days"),
            F.countDistinct("order_id").alias("frequency"),
            F.round(F.sum("sales"), 2).alias("monetary"),
        )
    )


# ============================================================ quintile scores
def add_rfm_scores(rfm: DataFrame) -> DataFrame:
    w_r = Window.orderBy(F.asc("recency_days"))   # smaller = better
    w_f = Window.orderBy(F.asc("frequency"))
    w_m = Window.orderBy(F.asc("monetary"))

    return (
        rfm
        .withColumn("_r_ntile", F.ntile(5).over(w_r))
        .withColumn("_f_ntile", F.ntile(5).over(w_f))
        .withColumn("_m_ntile", F.ntile(5).over(w_m))
        .withColumn("r_score", (6 - F.col("_r_ntile")).cast("int"))  # invert
        .withColumn("f_score", F.col("_f_ntile").cast("int"))
        .withColumn("m_score", F.col("_m_ntile").cast("int"))
        .drop("_r_ntile", "_f_ntile", "_m_ntile")
        .withColumn("rfm_score",
                    F.concat(F.col("r_score"), F.col("f_score"), F.col("m_score")))
    )


# ============================================================== KMeans + labels
def fit_kmeans(rfm: DataFrame, k: int = 5, seed: int = 42) -> DataFrame:
    features = ["recency_days", "frequency", "monetary"]

    assembler = VectorAssembler(inputCols=features, outputCol="features_raw")
    scaler = StandardScaler(inputCol="features_raw", outputCol="features",
                            withMean=True, withStd=True)

    assembled = assembler.transform(rfm)
    scaled = scaler.fit(assembled).transform(assembled)

    km = KMeans(featuresCol="features", predictionCol="cluster_id",
                k=k, seed=seed, maxIter=50)
    model = km.fit(scaled)

    return model.transform(scaled).drop("features", "features_raw")


def label_clusters(df: DataFrame) -> DataFrame:
    """Rule-based labels on top of cluster assignments.

    Label assignment uses the R/F/M scores (not raw cluster IDs) so the
    names are semantically correct regardless of sklearn/Spark's internal
    cluster numbering.
    """
    label = (
        F.when((F.col("r_score") >= 4) & (F.col("f_score") >= 4) & (F.col("m_score") >= 4), "Champions")
         .when((F.col("r_score") >= 3) & (F.col("f_score") >= 4) & (F.col("m_score") >= 3), "Loyal Customers")
         .when((F.col("r_score") >= 4) & (F.col("f_score") >= 2) & (F.col("m_score") >= 2), "Potential Loyalists")
         .when((F.col("r_score") <= 2) & (F.col("f_score") >= 3) & (F.col("m_score") >= 3), "At Risk")
         .when((F.col("r_score") <= 2) & (F.col("f_score") <= 2) & (F.col("m_score") <= 2), "Lost")
         .when((F.col("r_score") >= 4) & (F.col("f_score") == 1), "New Customers")
         .otherwise("Need Attention")
    )
    return df.withColumn("cluster_label", label)


# ================================================================ main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--silver-root", default=SILVER_ROOT)
    ap.add_argument("--gold-root", default=GOLD_ROOT)
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    print("=" * 70)
    print("  OpenBI — MLlib RFM + KMeans Segmentation")
    print("=" * 70)

    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    t0 = time.time()

    _section("Read Silver")
    fact = spark.read.format("delta").load(f"{args.silver_root}/fact_sales")
    dim_customer = spark.read.format("delta").load(f"{args.silver_root}/dim_customer")
    dim_date = spark.read.format("delta").load(f"{args.silver_root}/dim_date")
    print(f"  fact rows: {fact.count():,}")

    _section("Compute RFM")
    rfm = compute_rfm(fact, dim_customer, dim_date)
    n_cust = rfm.count()
    print(f"  customers: {n_cust:,}")

    _section("Score RFM quintiles")
    rfm = add_rfm_scores(rfm).cache()

    _section(f"Fit KMeans (k={args.k})")
    clustered = fit_kmeans(rfm, k=args.k)
    labelled = label_clusters(clustered)

    _section("Segment distribution")
    (
        labelled
        .groupBy("cluster_label")
        .agg(
            F.count("*").alias("customers"),
            F.round(F.avg("recency_days"), 1).alias("avg_recency"),
            F.round(F.avg("frequency"), 2).alias("avg_freq"),
            F.round(F.avg("monetary"), 2).alias("avg_monetary"),
        )
        .orderBy(F.desc("avg_monetary"))
        .show(truncate=False)
    )

    _section("Write to data/gold/customer_segments/")
    out = labelled.select(
        "customer_id", "customer_name", "segment",
        "recency_days", "frequency", "monetary",
        "r_score", "f_score", "m_score", "rfm_score",
        "cluster_id", "cluster_label",
    )
    (out.write
        .format("delta")
        .mode("overwrite")
        .save(f"{args.gold_root}/customer_segments"))
    print(f"  ✓ wrote {out.count():,} rows")

    print(f"\n  elapsed: {time.time() - t0:.1f}s")
    spark.stop()
    print("\n✓ RFM + KMeans segmentation complete")


if __name__ == "__main__":
    main()
