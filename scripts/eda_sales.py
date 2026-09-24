"""
OpenBI — Phase 1: Exploratory Data Analysis (Sales)

Run:
    python scripts/eda_sales.py

Outputs:
    - Full EDA report printed to terminal
    - PNG figures saved to reports/figures/
    - KPI candidate list written to docs/kpi_candidates.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "sample_superstore.csv"
FIG_DIR = ROOT / "reports" / "figures"
DOCS_DIR = ROOT / "docs"
KPI_PATH = DOCS_DIR / "kpi_candidates.md"

FIG_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid")
pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 160)


# ---------------------------------------------------------------- helpers
def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


def savefig(name: str) -> None:
    path = FIG_DIR / name
    plt.tight_layout()
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"  → saved figure: {path.relative_to(ROOT)}")


# ---------------------------------------------------------------- load
def load_data() -> pd.DataFrame:
    section("1. LOAD DATA")
    if not DATA_PATH.exists():
        sys.exit(f"ERROR: dataset not found at {DATA_PATH}")

    df = pd.read_csv(DATA_PATH, encoding="utf-8", low_memory=False)
    print(f"  File: {DATA_PATH.relative_to(ROOT)}")
    print(f"  Shape: {df.shape[0]:,} rows  ×  {df.shape[1]} columns")
    print(f"  Columns: {list(df.columns)}")
    return df


# ---------------------------------------------------------------- shape / dtypes
def inspect_shape(df: pd.DataFrame) -> None:
    section("2. STRUCTURE & DTYPES")
    info = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "non_null": df.notna().sum(),
        "null": df.isna().sum(),
        "null_pct": (df.isna().mean() * 100).round(2),
        "unique": df.nunique(dropna=True),
    })
    print(info.to_string())


# ---------------------------------------------------------------- dates
def inspect_dates(df: pd.DataFrame) -> None:
    section("3. DATE RANGE & GRANULARITY")

    date_cols = [c for c in df.columns if "date" in c.lower()]
    print(f"  Date-like columns detected: {date_cols}")

    for col in date_cols:
        parsed = pd.to_datetime(df[col], errors="coerce")
        print(f"\n  {col}:")
        print(f"    min          : {parsed.min()}")
        print(f"    max          : {parsed.max()}")
        print(f"    span         : {(parsed.max() - parsed.min()).days} days")
        print(f"    invalid rows : {parsed.isna().sum()}")

    # monthly row counts → detect granularity
    if "Order Date" in df.columns:
        orders = pd.to_datetime(df["Order Date"], errors="coerce")
        per_day = orders.dt.date.value_counts()
        print(f"\n  Orders per calendar day:")
        print(f"    distinct days       : {len(per_day)}")
        print(f"    avg rows/day        : {per_day.mean():.1f}")
        print(f"    busiest day         : {per_day.idxmax()} ({per_day.max()} rows)")


# ---------------------------------------------------------------- nulls / dups
def inspect_quality(df: pd.DataFrame) -> None:
    section("4. NULLS, DUPLICATES, UNIQUENESS")

    nulls = df.isna().sum().sort_values(ascending=False)
    nulls = nulls[nulls > 0]
    if nulls.empty:
        print("  ✓ No null values detected.")
    else:
        print("  Columns with nulls:")
        for c, n in nulls.items():
            print(f"    {c:30s} {n:>8,}  ({n / len(df) * 100:.2f}%)")

    dup_full = df.duplicated().sum()
    print(f"\n  Fully duplicated rows : {dup_full:,}")

    if "Order ID" in df.columns and "Product ID" in df.columns:
        dup_order_product = df.duplicated(subset=["Order ID", "Product ID"]).sum()
        print(f"  Duplicate (Order ID, Product ID) pairs : {dup_order_product:,}")

    if "Order ID" in df.columns:
        print(f"\n  Distinct Order IDs   : {df['Order ID'].nunique():,}")
        print(f"  Distinct Customer IDs: {df['Customer ID'].nunique():,}")
    if "Product ID" in df.columns:
        print(f"  Distinct Product IDs : {df['Product ID'].nunique():,}")


# ---------------------------------------------------------------- numeric stats
def inspect_numeric(df: pd.DataFrame) -> None:
    section("5. NUMERIC DISTRIBUTIONS")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    print(f"  Numeric columns: {numeric_cols}")

    if numeric_cols:
        print("\n  Describe:")
        print(df[numeric_cols].describe().T.to_string())

    # outliers via IQR
    print("\n  Outlier check (IQR method):")
    for c in numeric_cols:
        s = df[c].dropna()
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_out = ((s < lo) | (s > hi)).sum()
        print(f"    {c:15s}  outliers={n_out:>7,}  "
              f"({n_out / len(s) * 100:5.2f}%)  "
              f"bounds=[{lo:,.2f}, {hi:,.2f}]")

    # negative values worth flagging
    for c in ["Sales", "Quantity", "Profit", "Discount"]:
        if c in df.columns:
            neg = (df[c] < 0).sum()
            if neg:
                print(f"\n  ⚠ Negative '{c}' rows: {neg:,}")


# ---------------------------------------------------------------- plots
def plot_distributions(df: pd.DataFrame) -> None:
    section("6. DISTRIBUTION PLOTS")

    for col in ["Sales", "Profit", "Discount"]:
        if col not in df.columns:
            continue
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        sns.histplot(df[col], bins=50, ax=axes[0], color="steelblue")
        axes[0].set_title(f"{col} — histogram")
        sns.boxplot(x=df[col], ax=axes[1], color="salmon")
        axes[1].set_title(f"{col} — boxplot")
        savefig(f"dist_{col.lower()}.png")


def plot_revenue_by_month(df: pd.DataFrame) -> None:
    section("7. REVENUE BY MONTH")
    if "Order Date" not in df.columns or "Sales" not in df.columns:
        print("  skipped (missing Order Date or Sales)")
        return

    tmp = df.copy()
    tmp["Order Date"] = pd.to_datetime(tmp["Order Date"], errors="coerce")
    monthly = (tmp.set_index("Order Date")
                  .resample("MS")["Sales"].sum()
                  .reset_index())

    fig, ax = plt.subplots(figsize=(12, 4))
    sns.lineplot(data=monthly, x="Order Date", y="Sales", marker="o", ax=ax)
    ax.set_title("Monthly Revenue")
    ax.set_ylabel("Sales")
    savefig("revenue_by_month.png")

    print(monthly.to_string(index=False))


def plot_categorical_breakdowns(df: pd.DataFrame) -> None:
    section("8. REVENUE BY CATEGORY / REGION / SEGMENT")

    for col in ["Category", "Sub-Category", "Region", "Segment"]:
        if col not in df.columns or "Sales" not in df.columns:
            continue
        agg = (df.groupby(col, dropna=False)["Sales"].sum()
                 .sort_values(ascending=False))
        print(f"\n  Revenue by {col}:")
        print(agg.to_string())

        fig, ax = plt.subplots(figsize=(10, max(3, len(agg) * 0.35)))
        sns.barplot(x=agg.values, y=agg.index, ax=ax, palette="viridis")
        ax.set_title(f"Revenue by {col}")
        ax.set_xlabel("Sales")
        savefig(f"revenue_by_{col.lower().replace(' ', '_').replace('-', '_')}.png")


def plot_top_products(df: pd.DataFrame, n: int = 15) -> None:
    section(f"9. TOP {n} PRODUCTS BY REVENUE")
    name_col = next((c for c in df.columns if "product name" in c.lower()), None)
    if not name_col or "Sales" not in df.columns:
        print("  skipped (no product name column)")
        return

    top = (df.groupby(name_col)["Sales"].sum()
             .sort_values(ascending=False)
             .head(n))
    print(top.to_string())

    fig, ax = plt.subplots(figsize=(11, 6))
    sns.barplot(x=top.values, y=top.index, ax=ax, palette="magma")
    ax.set_title(f"Top {n} Products by Revenue")
    savefig("top_products.png")


def plot_profit_vs_discount(df: pd.DataFrame) -> None:
    section("10. PROFIT VS DISCOUNT")
    if not {"Profit", "Discount"}.issubset(df.columns):
        print("  skipped")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.scatterplot(data=df, x="Discount", y="Profit", alpha=0.4, ax=ax)
    ax.axhline(0, color="red", linestyle="--", linewidth=1)
    ax.set_title("Profit vs Discount")
    savefig("profit_vs_discount.png")

    # correlation
    corr = df[["Discount", "Profit", "Sales"]].corr(numeric_only=True)
    print("\n  Correlation matrix:")
    print(corr.round(3).to_string())


# ---------------------------------------------------------------- KPI candidates
def write_kpi_candidates(df: pd.DataFrame) -> None:
    section("11. KPI CANDIDATE LIST → docs/kpi_candidates.md")

    lines: list[str] = []
    add = lines.append

    add("# OpenBI — KPI Candidates\n")
    add("Auto-generated by `scripts/eda_sales.py`.\n")
    add(f"Dataset: `data/raw/sample_superstore.csv`  ")
    add(f"Rows: **{len(df):,}**  |  Columns: **{df.shape[1]}**\n")

    add("\n## Revenue & Profit\n")
    for k in [
        "Total Revenue = SUM(Sales)",
        "Total Profit = SUM(Profit)",
        "Profit Margin = SUM(Profit) / SUM(Sales)",
        "Average Order Value (AOV) = SUM(Sales) / COUNT(DISTINCT Order ID)",
        "Average Discount = AVG(Discount)",
        "Revenue MoM Growth = (Revenue_this_month - Revenue_prev_month) / Revenue_prev_month",
        "Revenue YoY Growth = (Revenue_this_year - Revenue_prev_year) / Revenue_prev_year",
    ]:
        add(f"- {k}")

    add("\n## Product\n")
    for k in [
        "Revenue by Category / Sub-Category",
        "Profit by Category / Sub-Category",
        "Top-N Products by Revenue",
        "Bottom-N Products by Profit (loss-makers)",
        "Discount sensitivity per Product",
    ]:
        add(f"- {k}")

    add("\n## Customer\n")
    for k in [
        "Revenue by Segment (Consumer / Corporate / Home Office)",
        "Revenue by Customer (Pareto / 80-20 check)",
        "Repeat-Purchase Rate",
        "Recency / Frequency / Monetary (RFM) — feeding segmentation",
        "Customer Lifetime Value (CLV) proxy = AVG(monetary) × frequency",
        "Churn flag (no orders in last N days)",
    ]:
        add(f"- {k}")

    add("\n## Geography\n")
    for k in [
        "Revenue by Region",
        "Revenue by State",
        "Revenue by City",
        "Profit Margin by Region",
    ]:
        add(f"- {k}")

    add("\n## Time\n")
    for k in [
        "Monthly / Quarterly Revenue Trend",
        "Seasonality (month-of-year index)",
        "Forecast horizon: next 30 / 90 days",
    ]:
        add(f"- {k}")

    add("\n## Inventory (only if Quantity + stock proxy available)\n")
    for k in [
        "Inventory Turnover",
        "Days of Inventory",
        "Stockout Risk (demand vs current stock)",
        "Dead Stock (no sales in N days)",
    ]:
        add(f"- {k}")

    add("\n---\n")
    add("## Dashboards to build (from Phase 3)\n")
    add("1. **Executive** — Revenue, Profit, Orders, Growth, Trend")
    add("2. **Sales** — Category / Region / Product drill-down")
    add("3. **Customer** — RFM segments, churn, CLV")

    KPI_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"  → wrote: {KPI_PATH.relative_to(ROOT)}")


# ---------------------------------------------------------------- main
def main() -> None:
    df = load_data()
    inspect_shape(df)
    inspect_dates(df)
    inspect_quality(df)
    inspect_numeric(df)
    plot_distributions(df)
    plot_revenue_by_month(df)
    plot_categorical_breakdowns(df)
    plot_top_products(df)
    plot_profit_vs_discount(df)
    write_kpi_candidates(df)

    section("DONE")
    print(f"  Figures : {FIG_DIR.relative_to(ROOT)}")
    print(f"  KPIs    : {KPI_PATH.relative_to(ROOT)}")
    print("\n  Next → Phase 2: build the Postgres warehouse.")


if __name__ == "__main__":
    main()
