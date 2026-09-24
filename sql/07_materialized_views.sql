-- OpenBI — 07 — materialized views for dashboards
-- Add when data grows; refresh with REFRESH MATERIALIZED VIEW.

DROP MATERIALIZED VIEW IF EXISTS warehouse.mv_monthly_revenue CASCADE;

CREATE MATERIALIZED VIEW warehouse.mv_monthly_revenue AS
SELECT * FROM warehouse.v_monthly_revenue;

CREATE UNIQUE INDEX IF NOT EXISTS mv_monthly_revenue_pk
    ON warehouse.mv_monthly_revenue(year, month);
