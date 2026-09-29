-- OpenBI — 10 — schema for Spark-published gold tables (v2)
-- Kept separate from `warehouse` (v1) so both can coexist in Superset.

CREATE SCHEMA IF NOT EXISTS warehouse_big;

-- monthly_revenue
DROP TABLE IF EXISTS warehouse_big.monthly_revenue CASCADE;
CREATE TABLE warehouse_big.monthly_revenue (
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    month_name      TEXT    NOT NULL,
    revenue         NUMERIC(18, 2) NOT NULL,
    profit          NUMERIC(18, 2) NOT NULL,
    orders          BIGINT  NOT NULL,
    avg_line_value  NUMERIC(18, 2) NOT NULL,
    PRIMARY KEY (year, month)
);

-- revenue_by_category
DROP TABLE IF EXISTS warehouse_big.revenue_by_category CASCADE;
CREATE TABLE warehouse_big.revenue_by_category (
    category        TEXT NOT NULL,
    sub_category    TEXT NOT NULL,
    revenue         NUMERIC(18, 2) NOT NULL,
    profit          NUMERIC(18, 2) NOT NULL,
    units           BIGINT NOT NULL,
    PRIMARY KEY (category, sub_category)
);

-- revenue_by_region
DROP TABLE IF EXISTS warehouse_big.revenue_by_region CASCADE;
CREATE TABLE warehouse_big.revenue_by_region (
    region          TEXT NOT NULL,
    state           TEXT NOT NULL,
    revenue         NUMERIC(18, 2) NOT NULL,
    profit          NUMERIC(18, 2) NOT NULL,
    PRIMARY KEY (region, state)
);

-- top_products
DROP TABLE IF EXISTS warehouse_big.top_products CASCADE;
CREATE TABLE warehouse_big.top_products (
    product_id      TEXT NOT NULL PRIMARY KEY,
    product_name    TEXT NOT NULL,
    category        TEXT NOT NULL,
    revenue         NUMERIC(18, 2) NOT NULL,
    profit          NUMERIC(18, 2) NOT NULL,
    units           BIGINT NOT NULL
);

-- customer_rfm
DROP TABLE IF EXISTS warehouse_big.customer_rfm CASCADE;
CREATE TABLE warehouse_big.customer_rfm (
    customer_id      TEXT NOT NULL PRIMARY KEY,
    customer_name    TEXT,
    segment          TEXT,
    recency_days     INTEGER NOT NULL,
    frequency        BIGINT  NOT NULL,
    monetary         NUMERIC(18, 2) NOT NULL,
    r_score          INTEGER NOT NULL,
    f_score          INTEGER NOT NULL,
    m_score          INTEGER NOT NULL,
    rfm_score        TEXT NOT NULL,
    cluster_label    TEXT NOT NULL
);

-- indexes for Superset filter performance
CREATE INDEX IF NOT EXISTS idx_big_monthly_year    ON warehouse_big.monthly_revenue(year);
CREATE INDEX IF NOT EXISTS idx_big_cat_category    ON warehouse_big.revenue_by_category(category);
CREATE INDEX IF NOT EXISTS idx_big_region_region   ON warehouse_big.revenue_by_region(region);
CREATE INDEX IF NOT EXISTS idx_big_rfm_cluster     ON warehouse_big.customer_rfm(cluster_label);
