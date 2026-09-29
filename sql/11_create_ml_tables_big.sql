-- OpenBI v2 — 11 — ML output tables in warehouse_big

DROP TABLE IF EXISTS warehouse_big.customer_segments CASCADE;
DROP TABLE IF EXISTS warehouse_big.sales_forecast    CASCADE;

-- -------------------- customer_segments --------------------
CREATE TABLE warehouse_big.customer_segments (
    customer_id      TEXT PRIMARY KEY,
    customer_name    TEXT,
    segment          TEXT,
    recency_days     INTEGER NOT NULL,
    frequency        BIGINT  NOT NULL,
    monetary         NUMERIC(18, 2) NOT NULL,
    r_score          INTEGER NOT NULL,
    f_score          INTEGER NOT NULL,
    m_score          INTEGER NOT NULL,
    rfm_score        TEXT    NOT NULL,
    cluster_id       INTEGER NOT NULL,
    cluster_label    TEXT    NOT NULL,
    computed_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_big_segments_cluster ON warehouse_big.customer_segments(cluster_id);
CREATE INDEX idx_big_segments_label   ON warehouse_big.customer_segments(cluster_label);

-- -------------------- sales_forecast --------------------
-- Composite PK: one row per (month, model). 3 models × 6 months = 18 rows.
CREATE TABLE warehouse_big.sales_forecast (
    forecast_month   DATE NOT NULL,
    model_name       TEXT NOT NULL,
    yhat             NUMERIC(18, 2) NOT NULL,
    yhat_lower       NUMERIC(18, 2),
    yhat_upper       NUMERIC(18, 2),
    is_winner        BOOLEAN DEFAULT FALSE,
    computed_at      TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (forecast_month, model_name)
);

CREATE INDEX idx_big_forecast_month ON warehouse_big.sales_forecast(forecast_month);
CREATE INDEX idx_big_forecast_model ON warehouse_big.sales_forecast(model_name);
