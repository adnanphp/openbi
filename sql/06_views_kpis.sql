-- OpenBI — 06 — KPI views for BI layer

DROP VIEW IF EXISTS warehouse.v_monthly_revenue     CASCADE;
DROP VIEW IF EXISTS warehouse.v_revenue_by_category CASCADE;
DROP VIEW IF EXISTS warehouse.v_revenue_by_region   CASCADE;
DROP VIEW IF EXISTS warehouse.v_top_products        CASCADE;
DROP VIEW IF EXISTS warehouse.v_customer_rfm        CASCADE;

-- Monthly revenue + profit
CREATE VIEW warehouse.v_monthly_revenue AS
SELECT
    d.year,
    d.month,
    d.month_name,
    SUM(f.sales)  AS revenue,
    SUM(f.profit) AS profit,
    COUNT(DISTINCT f.order_id) AS orders,
    ROUND(AVG(f.sales), 2)     AS avg_line_value
FROM warehouse.fact_sales f
JOIN warehouse.dim_date   d ON d.date_key = f.order_date_key
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;

-- Revenue by category
CREATE VIEW warehouse.v_revenue_by_category AS
SELECT
    p.category,
    p.sub_category,
    SUM(f.sales)  AS revenue,
    SUM(f.profit) AS profit,
    SUM(f.quantity) AS units
FROM warehouse.fact_sales f
JOIN warehouse.dim_product p ON p.product_key = f.product_key
GROUP BY p.category, p.sub_category
ORDER BY revenue DESC;

-- Revenue by region
CREATE VIEW warehouse.v_revenue_by_region AS
SELECT
    r.region,
    r.state,
    SUM(f.sales)  AS revenue,
    SUM(f.profit) AS profit
FROM warehouse.fact_sales f
JOIN warehouse.dim_region r ON r.region_key = f.region_key
GROUP BY r.region, r.state
ORDER BY revenue DESC;

-- Top products
CREATE VIEW warehouse.v_top_products AS
SELECT
    p.product_id,
    p.product_name,
    p.category,
    SUM(f.sales)   AS revenue,
    SUM(f.profit)  AS profit,
    SUM(f.quantity) AS units
FROM warehouse.fact_sales f
JOIN warehouse.dim_product p ON p.product_key = f.product_key
GROUP BY p.product_id, p.product_name, p.category
ORDER BY revenue DESC;

-- Customer RFM (raw, scoring happens in Phase 4)
CREATE VIEW warehouse.v_customer_rfm AS
WITH base AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.segment,
        MAX(d.full_date)                       AS last_order_date,
        COUNT(DISTINCT f.order_id)             AS frequency,
        SUM(f.sales)                           AS monetary
    FROM warehouse.fact_sales f
    JOIN warehouse.dim_customer c ON c.customer_key = f.customer_key
    JOIN warehouse.dim_date     d ON d.date_key     = f.order_date_key
    GROUP BY c.customer_id, c.customer_name, c.segment
)
SELECT
    customer_id,
    customer_name,
    segment,
    (CURRENT_DATE - last_order_date) AS recency_days,
    frequency,
    monetary,
    ROUND(monetary / NULLIF(frequency, 0), 2) AS avg_order_value
FROM base;
