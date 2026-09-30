{{ config(materialized='view') }}

SELECT
    customer_id,
    customer_name,
    segment,
    recency_days::int       AS recency_days,
    frequency::bigint       AS frequency,
    monetary::numeric(18,2) AS monetary,
    r_score::int            AS r_score,
    f_score::int            AS f_score,
    m_score::int            AS m_score,
    rfm_score,
    cluster_id::int         AS cluster_id,
    cluster_label
FROM {{ source('warehouse_big', 'customer_segments') }}
