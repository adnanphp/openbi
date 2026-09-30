{{ config(materialized='view') }}

SELECT
    product_id,
    product_name,
    category,
    revenue::numeric(18,2) AS revenue,
    profit::numeric(18,2)  AS profit,
    units::bigint          AS units
FROM {{ source('warehouse_big', 'top_products') }}
