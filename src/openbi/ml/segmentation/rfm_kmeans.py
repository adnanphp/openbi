"""OpenBI — KMeans clustering on RFM features + rule-based human labels.

We use KMeans to discover groups, but assign human labels via rules
based on R/F/M scores. This is the approach used by most RFM practitioners
and is more interpretable than sorting centroids by an arbitrary formula.
"""

from __future__ import annotations

import joblib
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from openbi.analytics.rfm import compute_rfm
from openbi.config.settings import settings
from openbi.utils.db import load_dataframe


def fit_kmeans(rfm: pd.DataFrame, k: int = 5, random_state: int = 42):
    features = rfm[["recency_days", "frequency", "monetary"]].copy()
    scaler = StandardScaler()
    X = scaler.fit_transform(features)
    km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    km.fit(X)
    return km, scaler, X


def rule_based_label(row: pd.Series) -> str:
    """Standard RFM segmentation rules.

    Based on r_score, f_score, m_score (each 1..5). Higher = better.
    """
    r, f, m = row["r_score"], row["f_score"], row["m_score"]

    # Champions: best on all three
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"

    # Loyal: good frequency + monetary, recent enough
    if r >= 3 and f >= 4 and m >= 3:
        return "Loyal Customers"

    # Potential Loyalist: recent, decent frequency, low-mid monetary
    if r >= 4 and f >= 2 and m >= 2:
        return "Potential Loyalists"

    # At Risk: used to be good, not recent
    if r <= 2 and f >= 3 and m >= 3:
        return "At Risk"

    # Lost: low on everything
    if r <= 2 and f <= 2 and m <= 2:
        return "Lost"

    # New: very recent, low frequency
    if r >= 4 and f == 1:
        return "New Customers"

    # Fallback — biggest remaining bucket
    return "Need Attention"


def main() -> None:
    print("=" * 70)
    print("  OpenBI — RFM + KMeans Segmentation")
    print("=" * 70)

    rfm = compute_rfm()
    print(f"  RFM rows: {len(rfm):,}")

    km, scaler, X = fit_kmeans(rfm, k=5)
    rfm["cluster_id"] = km.labels_
    rfm["cluster_label"] = rfm.apply(rule_based_label, axis=1)

    print("\n  Segment sizes:")
    print(rfm["cluster_label"].value_counts().to_string())

    print("\n  Segment averages:")
    print(
        rfm.groupby("cluster_label")[
            ["recency_days", "frequency", "monetary"]
        ].mean().round(2).sort_values("monetary", ascending=False).to_string()
    )

    # persist model
    settings.root.joinpath("models/segmentation").mkdir(parents=True, exist_ok=True)
    joblib.dump(km, settings.root / "models/segmentation/kmeans.pkl")
    joblib.dump(scaler, settings.root / "models/segmentation/scaler.pkl")
    print("\n  ✓ Model saved to models/segmentation/")

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
