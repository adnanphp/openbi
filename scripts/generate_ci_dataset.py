"""Generate a tiny deterministic dataset for CI.

CI doesn't need 1M rows — it needs the same schema with enough rows to
exercise joins, partitions, and dimension dedup. 10K rows is plenty.

Run:
    python scripts/generate_ci_dataset.py

Output:
    data/raw/big_superstore/part-00000.parquet   (~10K rows)
"""

from __future__ import annotations

from pathlib import Path

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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(SRC_CSV, encoding="utf-8", low_memory=False)
    df.columns = (
        df.columns.astype(str).str.strip().str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    df = df.rename(columns={c: PT_TO_EN.get(c, c) for c in df.columns})
    df["row_id"] = range(len(df))
    df["order_id"] = [f"CI-{i:07d}" for i in df["row_id"]]

    out = OUT_DIR / "part-00000.parquet"
    df.to_parquet(out, engine="pyarrow", compression="snappy", index=False)
    print(f"✓ wrote {len(df):,} rows to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
