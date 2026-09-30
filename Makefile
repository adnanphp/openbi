.PHONY: help up down logs psql init etl ml clean test cov

help:
	@echo "make up       - start all containers (Postgres + Superset)"
	@echo "make down     - stop containers"
	@echo "make logs     - tail Postgres logs"
	@echo "make psql     - open psql shell"
	@echo "make init     - up + wait + etl + ml  (full local bootstrap)"
	@echo "make etl      - run ETL only (assumes Postgres is up)"
	@echo "make ml       - run RFM + forecasting"
	@echo "make test     - run test suite"
	@echo "make cov      - run tests with coverage"
	@echo "make clean    - drop containers + volumes (destructive)"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f postgres

psql:
	docker exec -it openbi-postgres psql -U $${POSTGRES_USER:-openbi} -d openbi

# --- local bootstrap: start Postgres, wait for healthy, run ETL ---
wait-db:
	@echo "▶ Waiting for Postgres..."
	@until docker exec openbi-postgres pg_isready -U $${POSTGRES_USER:-openbi} >/dev/null 2>&1; do sleep 1; done
	@echo "✓ Postgres is up."

etl:
	bash scripts/init_db.sh

init: up wait-db etl ml
	@echo "✓ Local bootstrap complete."

ml:
	bash scripts/run_ml.sh

test:
	pytest tests -v

cov:
	pytest tests --cov=src/openbi --cov-report=term-missing --cov-report=html

clean:
	docker compose down -v

# ---- v2 (Spark + Delta) ----
bigdata-up:
	docker compose -f docker-compose.yml -f docker-compose.bigdata.yml up -d

bigdata-down:
	docker compose -f docker-compose.yml -f docker-compose.bigdata.yml down

bigdata:
	bash spark/jobs/run_bigdata_pipeline.sh

bigdata-test:
	docker exec -i openbi-spark-master python3 -m pytest \
		-p no:cacheprovider /opt/openbi/tests/ -v

bigdata-clean:
	rm -rf data/bronze/* data/silver/* data/gold/*

# ---- dbt ----
DBT_CMD = docker compose -f docker-compose.yml -f docker-compose.bigdata.yml -f docker-compose.dbt.yml run --rm dbt

dbt-build:
	$(DBT_CMD) dbt deps
	$(DBT_CMD) dbt build

dbt-run:
	$(DBT_CMD) dbt run

dbt-test:
	$(DBT_CMD) dbt test

dbt-docs:
	$(DBT_CMD) dbt docs generate
	@echo "run 'make dbt-docs-serve' in another terminal"

dbt-docs-serve:
	docker compose -f docker-compose.yml -f docker-compose.bigdata.yml -f docker-compose.dbt.yml up -d dbt-docs
	@echo "dbt docs at http://localhost:8085"

dbt-docs-stop:
	docker compose -f docker-compose.yml -f docker-compose.bigdata.yml -f docker-compose.dbt.yml stop dbt-docs
