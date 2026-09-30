{{ config(materialized='view') }}

SELECT
    category,
    sub_category,
    revenue::numeric(18,2) AS revenue,
    profit::numeric(18,2)  AS profit,
    units::bigint          AS units
FROM {{ source('warehouse_big', 'revenue_by_category') }}
