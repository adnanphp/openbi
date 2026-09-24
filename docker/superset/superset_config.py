"""
OpenBI — Superset configuration.

Metadata DB lives in a dedicated `superset_meta` schema inside the same
Postgres instance that hosts the warehouse. Warehouse tables are read-only
from Superset's perspective.

Env vars consumed (set in docker-compose.yml):
  SUPERSET_SECRET_KEY
  DATABASE_HOST, DATABASE_PORT, DATABASE_USER, DATABASE_PASSWORD, DATABASE_DB
"""

import os

# ---------------------------------------------------------------- core
SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

# Superset's metadata DB (NOT the warehouse)
SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://"
    f"{os.environ['DATABASE_USER']}:{os.environ['DATABASE_PASSWORD']}"
    f"@{os.environ['DATABASE_HOST']}:{os.environ['DATABASE_PORT']}"
    f"/{os.environ['DATABASE_DB']}"
)

# ---------------------------------------------------------------- cache
# Simple in-memory cache (fine for single-user portfolio).
# For multi-user, swap to Redis.
CACHE_CONFIG = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
}

# ---------------------------------------------------------------- features
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "DASHBOARD_RBAC": False,
    "EMBEDDED_SUPERSET": False,
    "ALERT_REPORTS": False,
}

# ---------------------------------------------------------------- security
# For local dev: allow HTTP, disable CSRF strictness for API imports later.
WTF_CSRF_ENABLED = True
WTF_CSRF_EXEMPT_LIST = []
TALISMAN_ENABLED = False

# ---------------------------------------------------------------- UI
APP_NAME = "OpenBI"
APP_ICON = "/static/assets/images/superset-logo-horiz.png"
LOGO_TOOLTIP = "OpenBI — Open-Source Business Intelligence"

# ---------------------------------------------------------------- lang
BABEL_DEFAULT_LOCALE = "en"
LANGUAGES = {
    "en": {"flag": "us", "name": "English"},
}

# ---------------------------------------------------------------- misc
ROW_LIMIT = 50000
SQLLAB_TIMEOUT = 300
SUPERSET_WEBSERVER_TIMEOUT = 300

# ---------------------------------------------------------------- async
# Disabled for single-container dev (no celery worker needed).
# Enable in Phase 5 when adding Airflow.
class CeleryConfig:  # noqa: D401
    broker_url = "redis://redis:6379/0"
    result_backend = "redis://redis:6379/0"
    worker_prefetch_multiplier = 1
    task_acks_late = True


# Uncomment to enable Celery (Phase 5):
# from celery.schedules import crontab
# CELERY_CONFIG = CeleryConfig
