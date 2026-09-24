-- OpenBI — 03 — typed staging view
-- Reads from staging.superstore_raw and casts to real types.
-- All columns are cast to TEXT first so this works whether the
-- staging table was created as text or as inferred numeric types.

DROP VIEW IF EXISTS staging.superstore CASCADE;

CREATE VIEW staging.superstore AS
SELECT
    NULLIF(row_id::TEXT, '')::INTEGER                 AS row_id,
    order_id,
    NULLIF(order_date::TEXT, '')::DATE                AS order_date,
    NULLIF(ship_date::TEXT, '')::DATE                 AS ship_date,
    ship_mode,
    customer_id,
    customer_name,
    segment,
    country,
    city,
    state,
    NULLIF(postal_code::TEXT, '')::TEXT               AS postal_code,
    region,
    product_id,
    category,
    sub_category,
    product_name,
    NULLIF(sales::TEXT, '')::NUMERIC(12, 4)           AS sales,
    NULLIF(quantity::TEXT, '')::INTEGER               AS quantity,
    NULLIF(discount::TEXT, '')::NUMERIC(5, 4)         AS discount,
    NULLIF(profit::TEXT, '')::NUMERIC(12, 4)          AS profit
FROM staging.superstore_raw;
