-- OpenBI Phase I — real-time streaming tables

CREATE SCHEMA IF NOT EXISTS warehouse_big;

DROP TABLE IF EXISTS warehouse_big.orders_realtime CASCADE;
CREATE TABLE warehouse_big.orders_realtime (
    event_id        TEXT PRIMARY KEY,
    event_time      TIMESTAMP,
    order_id        TEXT NOT NULL,
    customer_id     TEXT,
    customer_name   TEXT,
    segment         TEXT,
    category        TEXT,
    sub_category    TEXT,
    product_id      TEXT,
    region          TEXT,
    ship_mode       TEXT,
    quantity        INTEGER,
    sales           NUMERIC(14, 2),
    discount        NUMERIC(5, 4),
    profit          NUMERIC(14, 2),
    ingested_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_orders_rt_time     ON warehouse_big.orders_realtime(event_time DESC);
CREATE INDEX idx_orders_rt_category ON warehouse_big.orders_realtime(category);

-- Aggregated view that Superset will read
DROP VIEW IF EXISTS warehouse_big.orders_realtime_kpis;
CREATE VIEW warehouse_big.orders_realtime_kpis AS
SELECT
    category,
    COUNT(*)                    AS events,
    SUM(quantity)               AS total_units,
    ROUND(SUM(sales), 2)        AS revenue,
    ROUND(SUM(profit), 2)       AS profit,
    ROUND(AVG(sales), 2)        AS avg_order_value,
    MAX(event_time)             AS last_event
FROM warehouse_big.orders_realtime
GROUP BY category;
