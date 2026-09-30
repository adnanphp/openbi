{{ config(materialized='view') }}

SELECT
    year::int           AS year,
    month::int          AS month,
    month_name,
    revenue::numeric(18,2)      AS revenue,
    profit::numeric(18,2)       AS profit,
    orders::bigint              AS orders,
    avg_line_value::numeric(18,2) AS avg_line_value
FROM {{ source('warehouse_big', 'monthly_revenue') }}
