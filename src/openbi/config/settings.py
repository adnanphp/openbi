"""OpenBI — central settings loaded from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    # Postgres
    pg_host: str = os.getenv("POSTGRES_HOST", "localhost")
    pg_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    pg_db: str = os.getenv("POSTGRES_DB", "openbi")
    pg_user: str = os.getenv("POSTGRES_USER", "openbi")
    pg_password: str = os.getenv("POSTGRES_PASSWORD", "openbi")

    # App
    env: str = os.getenv("ENV", "dev")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Paths
    root: Path = ROOT
    data_raw: Path = ROOT / "data" / "raw"
    sql_dir: Path = ROOT / "sql"

    @property
    def database_url(self) -> str:
        url = os.getenv("DATABASE_URL")
        if url:
            return url
        return (
            f"postgresql+psycopg2://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )


settings = Settings()
