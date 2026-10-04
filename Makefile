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

# ---- Streaming (Phase I) ----
KAFKA_COMPOSE = docker compose -f docker-compose.yml -f docker-compose.bigdata.yml -f docker-compose.kafka.yml

streaming-up:
	$(KAFKA_COMPOSE) up -d kafka kafka-ui
	@echo "waiting 20s for kafka..."
	@sleep 20
	$(KAFKA_COMPOSE) exec -T kafka kafka-topics.sh --bootstrap-server localhost:9092 --create --if-not-exists --topic orders --partitions 3 --replication-factor 1 || true
	@echo "Kafka UI: http://localhost:8086"

streaming-down:
	$(KAFKA_COMPOSE) stop kafka kafka-ui

streaming-produce:
	python -m streaming.producer --bootstrap localhost:9092 --rate 5

streaming-bronze:
	$(KAFKA_COMPOSE) exec -T spark-master /opt/bitnami/spark/bin/spark-submit \
		--master spark://spark-master:7077 \
		--packages io.delta:delta-spark_2.12:3.1.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 \
		--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
		--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
		/opt/openbi/jobs/streaming/stream_orders.py

streaming-postgres:
	$(KAFKA_COMPOSE) exec -T spark-master /opt/bitnami/spark/bin/spark-submit \
		--master local[2] \
		--packages io.delta:delta-spark_2.12:3.1.0,org.postgresql:postgresql:42.7.3 \
		--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
		--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
		/opt/openbi/jobs/streaming/stream_to_postgres.py

streaming-status:
	docker exec openbi-postgres psql -U openbi -d openbi -c "SELECT COUNT(*) AS events, ROUND(SUM(sales),2) AS revenue FROM warehouse_big.orders_realtime;"

fix-perms:
	@mkdir -p data/bronze data/silver data/gold data/checkpoints
	@mkdir -p data/streaming/bronze_orders data/streaming/silver_orders
	@mkdir -p data/checkpoints/orders_bronze data/checkpoints/orders_postgres
	@sudo chmod -R 777 data/bronze data/silver data/gold data/checkpoints data/streaming
	@echo "✓ data folders are writable"

backup:
	@mkdir -p backups
	docker compose -f docker-compose.yml exec -T postgres pg_dump -U openbi openbi > backups/openbi_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✓ Backup written to backups/"

restore:
	@ls -t backups/*.sql | head -1 | xargs -I {} sh -c 'cat {} | docker compose -f docker-compose.yml exec -T postgres psql -U openbi -d openbi'
	@echo "✓ Restored from latest backup"

# ---- v2 ML ----
bigdata-ml:
	./spark/run_job.sh jobs/ml_rfm_kmeans.py
	./spark/run_job.sh jobs/ml_forecast.py
	./spark/run_job.sh jobs/publish_ml_to_postgres.py

bigdata-ml:
	./spark/run_job.sh jobs/ml_rfm_kmeans.py
	./spark/run_job.sh jobs/ml_forecast.py
	./spark/run_job.sh jobs/publish_ml_to_postgres.py
