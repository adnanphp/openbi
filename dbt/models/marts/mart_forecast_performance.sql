{{ config(materialized='table') }}

WITH ranked AS (
    SELECT
        forecast_month,
        model_name,
        yhat,
        -- Convert NaN (IEEE 754) and NULL to real NULL for downstream logic
        CASE WHEN yhat_lower = 'NaN'::numeric OR yhat_lower IS NULL
             THEN NULL ELSE yhat_lower END AS yhat_lower_clean,
        CASE WHEN yhat_upper = 'NaN'::numeric OR yhat_upper IS NULL
             THEN NULL ELSE yhat_upper END AS yhat_upper_clean,
        is_winner,
        ROW_NUMBER() OVER (PARTITION BY forecast_month ORDER BY is_winner DESC) AS rn
    FROM {{ ref('stg_sales_forecast') }}
)
SELECT
    forecast_month,
    model_name                                                       AS winning_model,
    yhat::numeric(18,2)                                              AS forecast_revenue,
    COALESCE(yhat_lower_clean, yhat * 0.85)::numeric(18,2)           AS yhat_lower,
    COALESCE(yhat_upper_clean, yhat * 1.15)::numeric(18,2)           AS yhat_upper,
    (yhat - COALESCE(yhat_lower_clean, yhat * 0.85))::numeric(18,2)  AS lower_uncertainty,
    (COALESCE(yhat_upper_clean, yhat * 1.15) - yhat)::numeric(18,2)  AS upper_uncertainty
FROM ranked
WHERE rn = 1
ORDER BY forecast_month
