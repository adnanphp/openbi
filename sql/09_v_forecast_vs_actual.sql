DROP VIEW IF EXISTS warehouse.v_forecast_vs_actual CASCADE;

CREATE VIEW warehouse.v_forecast_vs_actual AS
SELECT
    month,
    'actual'   AS series,
    revenue    AS yhat
FROM (
    SELECT MAKE_DATE(year, month, 1) AS month, SUM(revenue) AS revenue
    FROM warehouse.v_monthly_revenue
    GROUP BY year, month
) a
UNION ALL
SELECT
    forecast_month AS month,
    model_name     AS series,
    yhat
FROM warehouse.sales_forecast
WHERE is_winner = TRUE
ORDER BY month, series;
