-- OpenBI — 05 — populate fact_sales

INSERT INTO warehouse.fact_sales (
    order_id, row_id,
    customer_key, product_key, region_key, ship_mode_key,
    order_date_key, ship_date_key,
    sales, quantity, discount, profit
)
SELECT
    s.order_id,
    s.row_id,
    c.customer_key,
    p.product_key,
    r.region_key,
    sm.ship_mode_key,
    TO_CHAR(s.order_date, 'YYYYMMDD')::INTEGER  AS order_date_key,
    CASE WHEN s.ship_date IS NOT NULL
         THEN TO_CHAR(s.ship_date, 'YYYYMMDD')::INTEGER
         ELSE NULL END                          AS ship_date_key,
    s.sales,
    s.quantity,
    s.discount,
    s.profit
FROM staging.superstore s
JOIN warehouse.dim_customer  c  ON c.customer_id  = s.customer_id
JOIN warehouse.dim_product   p  ON p.product_id   = s.product_id
JOIN warehouse.dim_region    r  ON r.country      = s.country
                               AND r.region       = s.region
                               AND r.state        = s.state
                               AND r.city         = s.city
                               AND r.postal_code  IS NOT DISTINCT FROM s.postal_code
JOIN warehouse.dim_ship_mode sm ON sm.ship_mode   = s.ship_mode
WHERE s.order_date IS NOT NULL
ON CONFLICT (order_id, row_id) DO NOTHING;
