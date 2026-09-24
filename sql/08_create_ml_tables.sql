-- OpenBI — 08 — ML output tables
-- Populated by Python (rfm_kmeans.py, forecast models).
-- Rebuilt on every `make ml` run.

DROP TABLE IF EXISTS warehouse.customer_segments CASCADE;
DROP TABLE IF EXISTS warehouse.sales_forecast    CASCADE;

-- -------------------- customer_segments --------------------
CREATE TABLE warehouse.customer_segments (
    customer_id      TEXT PRIMARY KEY,
    customer_name    TEXT,
    segment          TEXT,      -- from dim_customer (Consumer / Corporate / Home Office)
    recency_days     INTEGER NOT NULL,
    frequency        INTEGER NOT NULL,
    monetary         NUMERIC(14, 2) NOT NULL,
    r_score          INTEGER NOT NULL,   -- 1..5
    f_score          INTEGER NOT NULL,   -- 1..5
    m_score          INTEGER NOT NULL,   -- 1..5
    rfm_score        TEXT    NOT NULL,   -- e.g. '555'
    cluster_id       INTEGER NOT NULL,   -- from KMeans
    cluster_label    TEXT    NOT NULL,   -- Champions / Loyal / At Risk / Lost / New
    computed_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_segments_cluster ON warehouse.customer_segments(cluster_id);
CREATE INDEX idx_segments_label   ON warehouse.customer_segments(cluster_label);

-- -------------------- sales_forecast --------------------
CREATE TABLE warehouse.sales_forecast (
    forecast_month   DATE PRIMARY KEY,
    model_name       TEXT NOT NULL,       -- 'baseline_ma', 'ets', 'xgboost'
    yhat             NUMERIC(14, 2) NOT NULL,
    yhat_lower       NUMERIC(14, 2),      -- optional prediction interval
    yhat_upper       NUMERIC(14, 2),
    is_winner        BOOLEAN DEFAULT FALSE, -- best model per horizon
    computed_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_forecast_model ON warehouse.sales_forecast(model_name);
