"""Validate RFM scoring logic."""

from __future__ import annotations

import pandas as pd
import pytest

from openbi.analytics.rfm import compute_rfm


@pytest.mark.skipif(
    "not config.getoption('--run-db')",
    reason="needs --run-db flag",
)
def test_rfm_scores_in_range():
    df = compute_rfm()
    assert len(df) > 0
    for col in ("r_score", "f_score", "m_score"):
        assert df[col].between(1, 5).all(), f"{col} out of range"


@pytest.mark.skipif(
    "not config.getoption('--run-db')",
    reason="needs --run-db flag",
)
def test_rfm_no_nulls():
    df = compute_rfm()
    assert df["customer_id"].notna().all()
    assert df["monetary"].notna().all()
    assert df["recency_days"].notna().all()
