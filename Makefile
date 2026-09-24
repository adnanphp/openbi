.PHONY: help up down logs psql init etl clean

help:
	@echo "make up       - start Postgres container"
	@echo "make down     - stop containers"
	@echo "make logs     - tail Postgres logs"
	@echo "make psql     - open psql shell"
	@echo "make init     - full init: container + ETL"
	@echo "make etl      - re-run ETL only"
	@echo "make clean    - drop container + volume (destructive)"

up:
	docker compose up -d postgres

down:
	docker compose down

logs:
	docker compose logs -f postgres

psql:
	docker exec -it openbi-postgres psql -U $${POSTGRES_USER:-openbi} -d openbi

init:
	bash scripts/init_db.sh

etl:
	bash scripts/run_etl.sh

clean:
	docker compose down -v
