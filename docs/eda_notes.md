# Phase 1 — EDA Notes

## Date range
- Order Date: ...
- Ship Date: ...

## Granularity
- Fact grain: one row per (Order ID, Product ID)  ← confirm

## Dimensions identified
- dim_customer  ← Customer ID, Customer Name, Segment
- dim_product   ← Product ID, Category, Sub-Category, Product Name
- dim_region    ← Country, Region, State, City, Postal Code
- dim_date      ← Order Date, Ship Date → calendar
- dim_ship_mode ← Ship Mode

## Measures (fact_sales)
- Sales, Quantity, Discount, Profit

## Degenerate dimensions (keep on fact)
- Order ID, Row ID

## Data quality flags
- ...

## KPIs confirmed buildable
- See docs/kpi_candidates.md
