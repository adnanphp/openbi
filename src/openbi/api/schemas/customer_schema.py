from __future__ import annotations

from pydantic import BaseModel


class SegmentSummary(BaseModel):
    cluster_label: str
    customers: int
    avg_recency_days: float
    avg_frequency: float
    avg_monetary: float
    total_monetary: float
