{{ config(materialized='view') }}

SELECT
    forecast_month,
    model_name,
    yhat::numeric(18,2)       AS yhat,
    yhat_lower::numeric(18,2) AS yhat_lower,
    yhat_upper::numeric(18,2) AS yhat_upper,
    is_winner
FROM {{ source('warehouse_big', 'sales_forecast') }}
