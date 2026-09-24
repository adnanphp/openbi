"""OpenBI — customer segmentation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import Connection

from openbi.api.dependencies import get_db
from openbi.api.schemas.customer_schema import SegmentSummary

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/segments", response_model=list[SegmentSummary])
def segments(db: Connection = Depends(get_db)) -> list[SegmentSummary]:
    sql = text("""
        SELECT
            cluster_label,
            COUNT(*)                    AS customers,
            AVG(recency_days)::numeric  AS avg_recency_days,
            AVG(frequency)::numeric     AS avg_frequency,
            AVG(monetary)::numeric      AS avg_monetary,
            SUM(monetary)::numeric      AS total_monetary
        FROM warehouse.customer_segments
        GROUP BY cluster_label
        ORDER BY total_monetary DESC
    """)
    return [
        SegmentSummary(
            cluster_label=r["cluster_label"],
            customers=int(r["customers"]),
            avg_recency_days=round(float(r["avg_recency_days"]), 1),
            avg_frequency=round(float(r["avg_frequency"]), 2),
            avg_monetary=round(float(r["avg_monetary"]), 2),
            total_monetary=round(float(r["total_monetary"]), 2),
        )
        for r in db.execute(sql).mappings()
    ]
