"""OpenBI — KMeans clustering on RFM features + human labels."""

from __future__ import annotations

import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from openbi.analytics.rfm import compute_rfm
from openbi.config.settings import settings
from openbi.utils.db import load_dataframe


# Human-readable label mapping — assigned after inspecting cluster centroids
# (see assign_labels() below; this dict is the fallback)
DEFAULT_LABELS = {
    0: "Champions",
    1: "Loyal Customers",
    2: "Potential Loyalists",
    3: "At Risk",
    4: "Lost",
}


def fit_kmeans(rfm: pd.DataFrame, k: int = 5, random_state: int = 42):
    features = rfm[["recency_days", "frequency", "monetary"]].copy()
    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    km.fit(X)

    return km, scaler, X


def assign_labels(rfm: pd.DataFrame, km: KMeans) -> dict[int, str]:
    """Map cluster IDs to business labels by inspecting centroids.

    Sort clusters by monetary (descending), then map to a fixed label order.
    This is deterministic regardless of sklearn's internal cluster numbering.
    """
    centroids = pd.DataFrame(
        km.cluster_centers_,
        columns=["recency_days", "frequency", "monetary"],
    )
    # rank by monetary (lower recency is better but raw units are days,
    # so we standardize the intent: high monetary + high frequency + low recency = best)
    centroids["score"] = (
        centroids["monetary"] * 1.0
        + centroids["frequency"] * 1.0
        - centroids["recency_days"] * 1.0
    )
    order = centroids["score"].sort_values(ascending=False).index.tolist()

    labels = ["Champions", "Loyal Customers", "Potential Loyalists",
              "At Risk", "Lost"]
    return {cluster_id: labels[i] for i, cluster_id in enumerate(order)}


def main() -> None:
    print("=" * 70)
    print("  OpenBI — RFM + KMeans Segmentation")
    print("=" * 70)

    rfm = compute_rfm()
    print(f"  RFM rows: {len(rfm):,}")

    km, scaler, X = fit_kmeans(rfm, k=5)
    rfm["cluster_id"] = km.labels_

    labels_map = assign_labels(rfm, km)
    rfm["cluster_label"] = rfm["cluster_id"].map(labels_map)

    print("\n  Cluster sizes:")
    print(rfm["cluster_label"].value_counts().to_string())

    print("\n  Cluster averages:")
    print(
        rfm.groupby("cluster_label")[
            ["recency_days", "frequency", "monetary"]
        ].mean().round(2).to_string()
    )

    # ---- persist model ----
    settings.root.joinpath("models/segmentation").mkdir(parents=True, exist_ok=True)
    joblib.dump(km, settings.root / "models/segmentation/kmeans.pkl")
    joblib.dump(scaler, settings.root / "models/segmentation/scaler.pkl")
    print("\n  ✓ Model saved to models/segmentation/")

    # ---- write to warehouse ----
    out = rfm[[
        "customer_id", "customer_name", "segment",
        "recency_days", "frequency", "monetary",
        "r_score", "f_score", "m_score", "rfm_score",
        "cluster_id", "cluster_label",
    ]].copy()
    out["monetary"] = out["monetary"].round(2)

    load_dataframe(out, table="customer_segments", schema="warehouse", if_exists="replace")
    print(f"  ✓ Wrote {len(out):,} rows to warehouse.customer_segments")


if __name__ == "__main__":
    main()
