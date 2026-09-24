"""OpenBI — load raw CSV into staging.

Handles both English and Portuguese Superstore variants by mapping
columns to canonical English snake_case names.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from openbi.config.settings import settings
from openbi.utils.db import execute_sql_string, load_dataframe, ping


# Portuguese → English column mapping
# (extends easily if you find more variants)
PT_TO_EN = {
    "linha_id":        "row_id",
    "ordem_id":        "order_id",
    "data_ordem":      "order_date",
    "data_envio":      "ship_date",
    "modo_envio":      "ship_mode",
    "cliente_id":      "customer_id",
    "nome_cliente":    "customer_name",
    "segmento":        "segment",
    "pais":            "country",
    "país":            "country",
    "cidade":          "city",
    "estado":          "state",
    "codigo_postal":   "postal_code",
    "regiao":          "region",
    "região":          "region",
    "produto_id":      "product_id",
    "categoria":       "category",
    "sub_categoria":   "sub_category",
    "nome_produto":    "product_name",
    "vendas":          "sales",
    "quantidade":      "quantity",
    "desconto":        "discount",
    "lucro":           "profit",
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase, snake_case, and translate to English."""
    df = df.copy()

    # 1. standard cleanup
    df.columns = (
        df.columns.astype(str)
                  .str.strip()
                  .str.lower()
                  .str.replace(" ", "_", regex=False)
                  .str.replace("-", "_", regex=False)
    )

    # 2. translate Portuguese → English
    df = df.rename(columns={c: PT_TO_EN.get(c, c) for c in df.columns})

    return df


def main() -> None:
    print("=" * 70)
    print("  OpenBI — Load CSV → staging.superstore_raw")
    print("=" * 70)

    csv_path = settings.data_raw / "sample_superstore.csv"
    if not csv_path.exists():
        sys.exit(f"ERROR: {csv_path} not found")

    if not ping():
        sys.exit("ERROR: cannot reach Postgres. Is `docker compose up -d` running?")

    # ensure schemas exist
    execute_sql_string("CREATE SCHEMA IF NOT EXISTS staging;")
    execute_sql_string("CREATE SCHEMA IF NOT EXISTS warehouse;")

    df = pd.read_csv(csv_path, encoding="utf-8", low_memory=False)
    print(f"  Read {len(df):,} rows × {df.shape[1]} cols from {csv_path.name}")
    print(f"  Raw columns: {list(df.columns)}")

    if len(df) < 100:
        print(f"  ⚠ WARNING: only {len(df)} rows — is this the real Superstore dataset?")

    df = normalize_columns(df)
    print(f"  Normalized columns: {list(df.columns)}")

    # sanity: verify expected columns exist
    expected = {
        "row_id", "order_id", "order_date", "ship_date", "ship_mode",
        "customer_id", "customer_name", "segment", "country", "city",
        "state", "postal_code", "region", "product_id", "category",
        "sub_category", "product_name", "sales", "quantity",
        "discount", "profit",
    }
    missing = expected - set(df.columns)
    if missing:
        print(f"  ⚠ WARNING: missing expected columns after translation: {sorted(missing)}")
    else:
        print("  ✓ All expected English columns present")

    df = df.astype(object).where(pd.notna(df), None)

    load_dataframe(df, table="superstore_raw", schema="staging", if_exists="replace")
    print("  ✓ Loaded into staging.superstore_raw")


if __name__ == "__main__":
    main()
