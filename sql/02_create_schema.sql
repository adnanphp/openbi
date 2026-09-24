-- OpenBI — 02 — star schema (dims + facts)

DROP TABLE IF EXISTS warehouse.fact_sales       CASCADE;
DROP TABLE IF EXISTS warehouse.dim_customer     CASCADE;
DROP TABLE IF EXISTS warehouse.dim_product      CASCADE;
DROP TABLE IF EXISTS warehouse.dim_region       CASCADE;
DROP TABLE IF EXISTS warehouse.dim_ship_mode    CASCADE;
DROP TABLE IF EXISTS warehouse.dim_date         CASCADE;

-- ---------------- dim_customer ----------------
CREATE TABLE warehouse.dim_customer (
    customer_key     SERIAL PRIMARY KEY,
    customer_id      TEXT NOT NULL UNIQUE,
    customer_name    TEXT,
    segment          TEXT
);

-- ---------------- dim_product ----------------
CREATE TABLE warehouse.dim_product (
    product_key      SERIAL PRIMARY KEY,
    product_id       TEXT NOT NULL UNIQUE,
    product_name     TEXT,
    category         TEXT,
    sub_category     TEXT
);

-- ---------------- dim_region ----------------
CREATE TABLE warehouse.dim_region (
    region_key       SERIAL PRIMARY KEY,
    country          TEXT,
    region           TEXT,
    state            TEXT,
    city             TEXT,
    postal_code      TEXT,
    UNIQUE (country, region, state, city, postal_code)
);

-- ---------------- dim_ship_mode ----------------
CREATE TABLE warehouse.dim_ship_mode (
    ship_mode_key    SERIAL PRIMARY KEY,
    ship_mode        TEXT NOT NULL UNIQUE
);

-- ---------------- dim_date ----------------
CREATE TABLE warehouse.dim_date (
    date_key         INTEGER PRIMARY KEY,     -- YYYYMMDD
    full_date        DATE NOT NULL UNIQUE,
    year             INTEGER NOT NULL,
    quarter          INTEGER NOT NULL,
    month            INTEGER NOT NULL,
    month_name       TEXT    NOT NULL,
    week             INTEGER NOT NULL,
    day_of_week      INTEGER NOT NULL,
    day_name         TEXT    NOT NULL,
    is_weekend       BOOLEAN NOT NULL
);

-- ---------------- fact_sales ----------------
CREATE TABLE warehouse.fact_sales (
    sales_key        BIGSERIAL PRIMARY KEY,
    order_id         TEXT    NOT NULL,
    row_id           INTEGER,
    customer_key     INTEGER NOT NULL REFERENCES warehouse.dim_customer(customer_key),
    product_key      INTEGER NOT NULL REFERENCES warehouse.dim_product(product_key),
    region_key       INTEGER NOT NULL REFERENCES warehouse.dim_region(region_key),
    ship_mode_key    INTEGER NOT NULL REFERENCES warehouse.dim_ship_mode(ship_mode_key),
    order_date_key   INTEGER NOT NULL REFERENCES warehouse.dim_date(date_key),
    ship_date_key    INTEGER          REFERENCES warehouse.dim_date(date_key),
    sales            NUMERIC(12, 4) NOT NULL,
    quantity         INTEGER        NOT NULL,
    discount         NUMERIC(5, 4)  NOT NULL,
    profit           NUMERIC(12, 4) NOT NULL,
    UNIQUE (order_id, row_id)
);

CREATE INDEX idx_fact_sales_order_date ON warehouse.fact_sales(order_date_key);
CREATE INDEX idx_fact_sales_customer   ON warehouse.fact_sales(customer_key);
CREATE INDEX idx_fact_sales_product    ON warehouse.fact_sales(product_key);
CREATE INDEX idx_fact_sales_region     ON warehouse.fact_sales(region_key);
