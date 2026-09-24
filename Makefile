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
