{{ config(materialized='view') }}

SELECT
    region,
    state,
    revenue::numeric(18,2) AS revenue,
    profit::numeric(18,2)  AS profit
FROM {{ source('warehouse_big', 'revenue_by_region') }}
