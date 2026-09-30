{{ config(materialized='table') }}

WITH monthly AS (
    SELECT
        year,
        month,
        revenue,
        profit
    FROM {{ ref('stg_monthly_revenue') }}
),
rollup AS (
    SELECT
        year,
        SUM(revenue)   AS year_revenue,
        SUM(profit)    AS year_profit,
        SUM(revenue) / NULLIF(SUM(profit), 0) AS revenue_to_profit,
        COUNT(*)       AS months_reported
    FROM monthly
    GROUP BY year
)
SELECT
    r.year,
    r.year_revenue,
    r.year_profit,
    ROUND(100.0 * r.year_profit / NULLIF(r.year_revenue, 0), 2) AS profit_margin_pct,
    r.revenue_to_profit,
    r.months_reported,
    LAG(r.year_revenue) OVER (ORDER BY r.year)                          AS prev_year_revenue,
    ROUND(100.0 * (r.year_revenue - LAG(r.year_revenue) OVER (ORDER BY r.year))
        / NULLIF(LAG(r.year_revenue) OVER (ORDER BY r.year), 0), 2)     AS yoy_growth_pct
FROM rollup r
ORDER BY r.year
