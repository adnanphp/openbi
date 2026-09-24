"""Validate KPI math on synthetic data (no DB required)."""

from __future__ import annotations

import numpy as np


def test_revenue_profit_relationship():
    revenue = np.array([100.0, 200.0, 300.0])
    profit = np.array([10.0, 20.0, 30.0])
    margin = profit.sum() / revenue.sum()
    assert abs(margin - 0.10) < 1e-9


def test_aov_math():
    revenue = 1000.0
    orders = 4
    assert revenue / orders == 250.0
