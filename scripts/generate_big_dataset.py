"""Generate a large synthetic Superstore dataset for Spark.

Reads the small 10K-row Superstore CSV and emits a large Parquet dataset
by replicating + jittering it, written in chunks (memory-safe).

Uses a bounded pool of customers/products so the resulting Silver star
schema has realistic cardinality:
  - ~800 unique customers   (matches real Superstore)
  - ~1,900 unique products
  - 4 ship modes
  - ~630 regions

Run:
    python scripts/generate_big_dataset.py --rows 1_000_000 --chunk-size 500_000
    python scripts/generate_big_dataset.py --rows 100_000_000 --chunk-size 1_000_000
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC_CSV = ROOT / "data" / "raw" / "sample_superstore.csv"
OUT_DIR = ROOT / "data" / "raw" / "big_superstore"

PT_TO_EN = {
    "linha_id": "row_id", "ordem_id": "order_id",
    "data_ordem": "order_date", "data_envio": "ship_date",
    "modo_envio": "ship_mode", "cliente_id": "customer_id",
    "nome_cliente": "customer_name", "segmento": "segment",
    "pais": "country", "país": "country", "cidade": "city",
    "estado": "state", "codigo_postal": "postal_code",
    "regiao": "region", "região": "region",
    "produto_id": "product_id", "categoria": "category",
    "sub_categoria": "sub_category", "nome_produto": "product_name",
    "vendas": "sales", "quantidade": "quantity",
    "desconto": "discount", "lucro": "profit",
}


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str).str.strip().str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    return df.rename(columns={c: PT_TO_EN.get(c, c) for c in df.columns})


def _make_pool(seed_df: pd.DataFrame, size: int, prefix: str) -> pd.DataFrame:
    """Build a fixed pool of dimension rows by sampling `size` from seed_df."""
    rng = np.random.default_rng(42)
    idx = rng.integers(0, len(seed_df), size=size)
    pool = seed_df.iloc[idx].copy().reset_index(drop=True)
    # Assign deterministic IDs so each pool row is stable across runs
    pool["_pool_id"] = [f"{prefix}-{i:06d}" for i in range(size)]
    return pool


def _jitter_dates(series: pd.Series, seed: int) -> pd.Series:
    rng = np.random.default_rng(seed)
    days = rng.integers(-730, 730, size=len(series))
    return pd.to_datetime(series) + pd.to_timedelta(days, unit="D")


def generate(total_rows: int, chunk_size: int, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"▶ Reading seed CSV: {SRC_CSV.name}")
    base = _normalize(pd.read_csv(SRC_CSV, encoding="utf-8", low_memory=False))
    print(f"  seed rows: {len(base):,}")

    # ---- fixed dimension pools (bounded cardinality) ----
    N_CUSTOMERS = 800
    N_PRODUCTS = 1900
    customer_pool = _make_pool(base, N_CUSTOMERS, "CUST")
    product_pool = _make_pool(base, N_PRODUCTS, "PROD")
    print(f"  customer pool: {N_CUSTOMERS}")
    print(f"  product pool : {N_PRODUCTS}")

    n_chunks = math.ceil(total_rows / chunk_size)
    rows_written = 0
    t0 = time.time()

    for i in range(n_chunks):
        this_chunk = min(chunk_size, total_rows - rows_written)

        # sample pool indices — this is where cardinality is preserved
        cust_idx = rng.integers(0, N_CUSTOMERS, size=this_chunk)
        prod_idx = rng.integers(0, N_PRODUCTS, size=this_chunk)

        chunk = pd.DataFrame({
            "row_id":      np.arange(rows_written, rows_written + this_chunk),
            "order_id":    [f"BIG-{i:05d}-{j:08d}" for j in range(this_chunk)],
            "order_date":  _jitter_dates(
                base["order_date"].iloc[rng.integers(0, len(base), this_chunk)].reset_index(drop=True),
                seed + i,
            ),
            "ship_date":   _jitter_dates(
                base["ship_date"].iloc[rng.integers(0, len(base), this_chunk)].reset_index(drop=True),
                seed + i + 1,
            ),
            "ship_mode":   base["ship_mode"].iloc[rng.integers(0, len(base), this_chunk)].reset_index(drop=True),
            "customer_id": customer_pool["_pool_id"].iloc[cust_idx].reset_index(drop=True),
            "customer_name": customer_pool["customer_name"].iloc[cust_idx].reset_index(drop=True),
            "segment":     customer_pool["segment"].iloc[cust_idx].reset_index(drop=True),
            "country":     base["country"].iloc[rng.integers(0, len(base), this_chunk)].reset_index(drop=True),
            "city":        base["city"].iloc[rng.integers(0, len(base), this_chunk)].reset_index(drop=True),
            "state":       base["state"].iloc[rng.integers(0, len(base), this_chunk)].reset_index(drop=True),
            "postal_code": base["postal_code"].iloc[rng.integers(0, len(base), this_chunk)].reset_index(drop=True),
            "region":      base["region"].iloc[rng.integers(0, len(base), this_chunk)].reset_index(drop=True),
            "product_id":  product_pool["_pool_id"].iloc[prod_idx].reset_index(drop=True),
            "category":    product_pool["category"].iloc[prod_idx].reset_index(drop=True),
            "sub_category": product_pool["sub_category"].iloc[prod_idx].reset_index(drop=True),
            "product_name": product_pool["product_name"].iloc[prod_idx].reset_index(drop=True),
            "sales":       (base["sales"].iloc[rng.integers(0, len(base), this_chunk)].values
                            * rng.uniform(0.5, 2.0, size=this_chunk)).round(4),
            "quantity":    (base["quantity"].iloc[rng.integers(0, len(base), this_chunk)].values
                            + rng.integers(-2, 4, size=this_chunk)).clip(min=1).astype(int),
            "discount":    base["discount"].iloc[rng.integers(0, len(base), this_chunk)].reset_index(drop=True),
            "profit":      (base["profit"].iloc[rng.integers(0, len(base), this_chunk)].values
                            * rng.uniform(0.5, 2.0, size=this_chunk)).round(4),
        })

        chunk = chunk.astype(object).where(pd.notna(chunk), None)

        out_path = OUT_DIR / f"part-{i:05d}.parquet"
        chunk.to_parquet(out_path, engine="pyarrow", compression="snappy", index=False)

        rows_written += len(chunk)
        elapsed = time.time() - t0
        rate = rows_written / elapsed if elapsed > 0 else 0
        print(f"  [{i+1:>4}/{n_chunks}] {rows_written:>12,} rows  ({rate:,.0f} rows/s)")

    print(f"\n✓ Done. {rows_written:,} rows written to {OUT_DIR.relative_to(ROOT)}")
    total_bytes = sum(p.stat().st_size for p in OUT_DIR.glob("*.parquet"))
    print(f"  Total size: {total_bytes / 1e9:.2f} GB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=1_000_000)
    ap.add_argument("--chunk-size", type=int, default=500_000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if not SRC_CSV.exists():
        sys.exit(f"ERROR: seed CSV not found at {SRC_CSV}")

    generate(args.rows, args.chunk_size, args.seed)


if __name__ == "__main__":
    main()
