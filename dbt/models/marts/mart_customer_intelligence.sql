{{ config(materialized='table') }}

SELECT
    cluster_label,
    COUNT(*)                              AS customers,
    ROUND(AVG(recency_days), 1)           AS avg_recency_days,
    ROUND(AVG(frequency), 2)              AS avg_frequency,
    ROUND(AVG(monetary), 2)               AS avg_monetary,
    ROUND(SUM(monetary), 2)               AS total_monetary,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)  AS pct_of_customers,
    ROUND(100.0 * SUM(monetary)
        / NULLIF(SUM(SUM(monetary)) OVER (), 0), 2)     AS pct_of_revenue
FROM {{ ref('stg_customer_segments') }}
GROUP BY cluster_label
ORDER BY total_monetary DESC
