"""Shared fixtures + pytest options."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def pytest_addoption(parser):
    parser.addoption(
        "--run-db", action="store_true", default=False,
        help="run tests that require a live Postgres warehouse",
    )
