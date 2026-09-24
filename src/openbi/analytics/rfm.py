"""OpenBI — RFM scoring.

Reads warehouse.fact_sales, computes Recency / Frequency / Monetary per customer.
Recency is anchored to the most recent order date in the data (not CURRENT_DATE),
which is the correct choice for historical datasets like Superstore.

Scores each metric 1..5 by quintile. Returns a DataFrame.
"""

from __future__ import annotations

import pandas as pd

from openbi.utils.db import read_sql


def compute_rfm() -> pd.DataFrame:
    """Return per-customer RFM table with r/f/m scores 1..5."""
    sql = """
        WITH anchor AS (
            SELECT MAX(d.full_date) AS snapshot_date
            FROM warehouse.fact_sales f
            JOIN warehouse.dim_date d ON d.date_key = f.order_date_key
        ),
        base AS (
            SELECT
                c.customer_id,
                c.customer_name,
                c.segment,
                MAX(d.full_date)            AS last_order_date,
                COUNT(DISTINCT f.order_id)  AS frequency,
                SUM(f.sales)                AS monetary
            FROM warehouse.fact_sales f
            JOIN warehouse.dim_customer c ON c.customer_key = f.customer_key
            JOIN warehouse.dim_date     d ON d.date_key     = f.order_date_key
            GROUP BY c.customer_id, c.customer_name, c.segment
        )
        SELECT
            b.customer_id,
            b.customer_name,
            b.segment,
            (a.snapshot_date - b.last_order_date) AS recency_days,
            b.frequency,
            b.monetary
        FROM base b CROSS JOIN anchor a
    """
    df = read_sql(sql)
    df["monetary"] = df["monetary"].astype(float)
    df["frequency"] = df["frequency"].astype(int)
    df["recency_days"] = df["recency_days"].astype(int)

    # ---- quintile scores (5 = best, 1 = worst) ----
    # Recency: fewer days = better → invert
    df["r_score"] = pd.qcut(
        df["recency_days"].rank(method="first"),
        5, labels=[5, 4, 3, 2, 1],
    ).astype(int)

    # Frequency: more orders = better
    df["f_score"] = pd.qcut(
        df["frequency"].rank(method="first"),
        5, labels=[1, 2, 3, 4, 5],
    ).astype(int)

    # Monetary: higher = better
    df["m_score"] = pd.qcut(
        df["monetary"].rank(method="first"),
        5, labels=[1, 2, 3, 4, 5],
    ).astype(int)

    df["rfm_score"] = (
        df["r_score"].astype(str)
        + df["f_score"].astype(str)
        + df["m_score"].astype(str)
    )
    df["rfm_sum"] = df["r_score"] + df["f_score"] + df["m_score"]
    return df


if __name__ == "__main__":
    rfm = compute_rfm()
    print(rfm.head(20).to_string())
    print(f"\nRows: {len(rfm):,}")
    print(f"\nRecency stats (should now be small — days since last order):")
    print(rfm["recency_days"].describe().to_string())
    print(f"\nScore distributions:")
    print(rfm[["r_score", "f_score", "m_score"]].describe().to_string())
