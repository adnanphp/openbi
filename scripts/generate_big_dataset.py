"""Generate a large synthetic Superstore dataset for Spark.

Reads the small 10K-row Superstore CSV and emits a 100M+ row Parquet
dataset by replicating + jittering it, written in chunks (memory-safe).

Run:
    python scripts/generate_big_dataset.py --rows 100_000_000
    python scripts/generate_big_dataset.py --rows 1_000_000   # quick test

Output:
    data/raw/big_superstore/part-*.parquet
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

# column-name normalization matching load_csv.py
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


def _synth_customer_id(n: int) -> list[str]:
    """Fake but valid-looking customer IDs: 'XX-#####'."""
    letters = np.random.choice(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), size=n)
    letters2 = np.random.choice(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), size=n)
    digits = np.random.randint(10000, 99999, size=n)
    return [f"{a}{b}-{d}" for a, b, d in zip(letters, letters2, digits)]


def _synth_product_id(n: int) -> list[str]:
    """Fake product IDs: 'CAT-XX-#########'."""
    cats = np.random.choice(["FUR", "OFF", "TEC"], size=n)
    letters = np.random.choice(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), size=n)
    letters2 = np.random.choice(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), size=n)
    digits = np.random.randint(100000000, 999999999, size=n)
    return [f"{c}-{a}{b}-{d}" for c, a, b, d in zip(cats, letters, letters2, digits)]


def _jitter_dates(series: pd.Series, seed: int) -> pd.Series:
    """Randomly shift dates ±2 years to expand the time range."""
    rng = np.random.default_rng(seed)
    days = rng.integers(-730, 730, size=len(series))
    return pd.to_datetime(series) + pd.to_timedelta(days, unit="D")


def generate(total_rows: int, chunk_size: int, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"▶ Reading seed CSV: {SRC_CSV.name}")
    base = _normalize(pd.read_csv(SRC_CSV, encoding="utf-8", low_memory=False))
    print(f"  seed rows: {len(base):,}")

    n_chunks = math.ceil(total_rows / chunk_size)
    rows_written = 0
    t0 = time.time()

    for i in range(n_chunks):
        # sample from base, with replacement, chunk_size rows
        idx = rng.integers(0, len(base), size=chunk_size)
        chunk = base.iloc[idx].copy().reset_index(drop=True)

        # -- new unique IDs so no dupes across chunks --
        chunk["order_id"] = [
            f"BIG-{i:05d}-{j:08d}" for j in range(len(chunk))
        ]
        chunk["row_id"] = np.arange(rows_written, rows_written + len(chunk))
        chunk["customer_id"] = _synth_customer_id(len(chunk))
        chunk["product_id"] = _synth_product_id(len(chunk))

        # -- jitter dates so the time range spans 2012–2024 --
        chunk["order_date"] = _jitter_dates(chunk["order_date"], seed + i)
        chunk["ship_date"] = _jitter_dates(chunk["ship_date"], seed + i + 1)

        # -- numeric jitter: multiply sales/profit/quantity by a small factor --
        for col in ("sales", "profit"):
            if col in chunk.columns:
                factor = rng.uniform(0.5, 2.0, size=len(chunk))
                chunk[col] = (chunk[col].astype(float) * factor).round(4)
        if "quantity" in chunk.columns:
            chunk["quantity"] = (
                chunk["quantity"].astype(int)
                + rng.integers(-2, 4, size=len(chunk))
            ).clip(lower=1)

        # -- type cleanup for Parquet --
        chunk = chunk.astype(object).where(pd.notna(chunk), None)

        out_path = OUT_DIR / f"part-{i:05d}.parquet"
        chunk.to_parquet(out_path, engine="pyarrow", compression="snappy", index=False)

        rows_written += len(chunk)
        elapsed = time.time() - t0
        rate = rows_written / elapsed if elapsed > 0 else 0
        print(f"  [{i+1:>4}/{n_chunks}] {rows_written:>12,} rows  "
              f"({rate:,.0f} rows/s)  → {out_path.name}")

    print(f"\n✓ Done. {rows_written:,} rows written to {OUT_DIR.relative_to(ROOT)}")
    total_bytes = sum(p.stat().st_size for p in OUT_DIR.glob("*.parquet"))
    print(f"  Total size: {total_bytes / 1e9:.2f} GB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=1_000_000,
                    help="total rows to generate (default 1M for testing)")
    ap.add_argument("--chunk-size", type=int, default=500_000,
                    help="rows per Parquet file (default 500K)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if not SRC_CSV.exists():
        sys.exit(f"ERROR: seed CSV not found at {SRC_CSV}")

    generate(args.rows, args.chunk_size, args.seed)


if __name__ == "__main__":
    main()
