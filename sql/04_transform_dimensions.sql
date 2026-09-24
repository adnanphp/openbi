-- OpenBI — 04 — populate dimensions

-- dim_customer
INSERT INTO warehouse.dim_customer (customer_id, customer_name, segment)
SELECT DISTINCT
    customer_id,
    customer_name,
    segment
FROM staging.superstore
WHERE customer_id IS NOT NULL
ON CONFLICT (customer_id) DO NOTHING;

-- dim_product
INSERT INTO warehouse.dim_product (product_id, product_name, category, sub_category)
SELECT DISTINCT
    product_id,
    product_name,
    category,
    sub_category
FROM staging.superstore
WHERE product_id IS NOT NULL
ON CONFLICT (product_id) DO NOTHING;

-- dim_region
INSERT INTO warehouse.dim_region (country, region, state, city, postal_code)
SELECT DISTINCT
    country,
    region,
    state,
    city,
    postal_code
FROM staging.superstore
WHERE city IS NOT NULL
ON CONFLICT (country, region, state, city, postal_code) DO NOTHING;

-- dim_ship_mode
INSERT INTO warehouse.dim_ship_mode (ship_mode)
SELECT DISTINCT ship_mode
FROM staging.superstore
WHERE ship_mode IS NOT NULL
ON CONFLICT (ship_mode) DO NOTHING;

-- dim_date — build calendar covering BOTH order_date and ship_date
INSERT INTO warehouse.dim_date (
    date_key, full_date, year, quarter, month, month_name,
    week, day_of_week, day_name, is_weekend
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER            AS date_key,
    d::DATE                                    AS full_date,
    EXTRACT(YEAR    FROM d)::INTEGER           AS year,
    EXTRACT(QUARTER FROM d)::INTEGER           AS quarter,
    EXTRACT(MONTH   FROM d)::INTEGER           AS month,
    TO_CHAR(d, 'Mon')                          AS month_name,
    EXTRACT(WEEK    FROM d)::INTEGER           AS week,
    EXTRACT(DOW     FROM d)::INTEGER           AS day_of_week,
    TO_CHAR(d, 'Dy')                           AS day_name,
    EXTRACT(DOW FROM d) IN (0, 6)              AS is_weekend
FROM generate_series(
    LEAST(
        (SELECT MIN(order_date) FROM staging.superstore),
        (SELECT MIN(ship_date)  FROM staging.superstore)
    ),
    GREATEST(
        (SELECT MAX(order_date) FROM staging.superstore),
        (SELECT MAX(ship_date)  FROM staging.superstore)
    ),
    INTERVAL '1 day'
) AS d
ON CONFLICT (date_key) DO NOTHING;
