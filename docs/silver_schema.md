# OpenBI — Silver Layer (Star Schema in Delta Lake)

The Silver layer transforms the 1M-row Bronze Delta table into a proper
star schema: 5 dimensions + 1 fact, all as Delta tables.

## Lineage
data/bronze/sales/ (Delta, partitioned by category)
│
│ PySpark: dropDuplicates + row_number() → surrogate keys
▼
data/silver/dim_customer/ (Delta)
data/silver/dim_product/ (Delta)
data/silver/dim_region/ (Delta)
data/silver/dim_ship_mode/ (Delta)
data/silver/dim_date/ (Delta, generated calendar)
│
│ PySpark: inner joins → FK resolution
▼
data/silver/fact_sales/ (Delta, partitioned by year)

text

## Tables

### dim_customer
| Column | Type | Notes |
|---|---|---|
| customer_key | int | surrogate, deterministic |
| customer_id | string | natural key |
| customer_name | string | |
| segment | string | Consumer / Corporate / Home Office |

### dim_product
| Column | Type | Notes |
|---|---|---|
| product_key | int | surrogate |
| product_id | string | natural key |
| product_name | string | |
| category | string | Furniture / Office Supplies / Technology |
| sub_category | string | |

### dim_region
| Column | Type | Notes |
|---|---|---|
| region_key | int | surrogate |
| country, region, state, city, postal_code | string/long | natural composite |

### dim_ship_mode
| Column | Type | Notes |
|---|---|---|
| ship_mode_key | int | surrogate |
| ship_mode | string | First Class / Second Class / Standard Class / Same Day |

### dim_date
| Column | Type | Notes |
|---|---|---|
| date_key | int | `yyyyMMdd` (matches v1 Postgres) |
| full_date | date | unique |
| year, quarter, month | int | |
| month_name | string | Jan..Dec |
| week | int | ISO week |
| day_of_week | int | 1=Sun .. 7=Sat (Spark convention) |
| day_name | string | Sun..Sat |
| is_weekend | boolean | Sat/Sun |

### fact_sales
| Column | Type | Notes |
|---|---|---|
| order_id | string | degenerate dimension |
| row_id | long | degenerate dimension |
| customer_key | int | FK → dim_customer |
| product_key | int | FK → dim_product |
| region_key | int | FK → dim_region |
| ship_mode_key | int | FK → dim_ship_mode |
| order_date_key | int | FK → dim_date |
| ship_date_key | int | FK → dim_date (nullable) |
| sales | double | measure |
| quantity | long | measure |
| discount | double | measure |
| profit | double | measure |
| year | int | partition column |

**Grain:** one row per `(order_id, row_id)`.
**Partitioning:** `year`.

## Design decisions

1. **Deterministic surrogate keys.** `row_number() OVER (ORDER BY natural_key)`
   produces the same key values on every rerun.

2. **Partition fact by year.** All dashboards filter by time.

3. **Same column names as v1 Postgres.** Phase C publishes gold aggregates
   back to Postgres and Superset + FastAPI keep working unchanged.

4. **`ship_date_key` left join.** Null ship dates preserved.

5. **Idempotent.** `mode("overwrite")` on all writes.

## Running

```bash
./spark/run_job.sh jobs/bronze_to_silver.py

docker exec -i openbi-spark-master python3 -m pytest \
  -p no:cacheprovider /opt/openbi/tests/test_silver.py -v
