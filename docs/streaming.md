# OpenBI — Real-Time Streaming (Phase I)

Kafka + Spark Structured Streaming pipeline running alongside the batch
pipeline. Events flow from a producer → Kafka → Delta Bronze → Postgres
→ Superset real-time dashboard.

## Architecture
streaming/producer.py
│
│ 5 events/sec (configurable)
▼
Kafka: topic "orders" (3 partitions, 24h retention)
│
▼
Spark Structured Streaming: stream_orders.py
│ micro-batch every 10s
▼
data/streaming/bronze_orders/ (Delta, ACID)
│
▼
Spark Structured Streaming: stream_to_postgres.py
│ micro-batch every 10s
▼
warehouse_big.orders_realtime (Postgres)
│
▼
Superset "Real-Time Orders" dashboard (5s refresh)

text

## Components

| Component | Port | Purpose |
|---|---|---|
| Kafka (KRaft) | 9092 | Message broker, no ZooKeeper |
| Kafka UI | 8086 | Topic browser |
| producer.py | — | Synthetic order events |
| stream_orders.py | — | Kafka → Delta Bronze |
| stream_to_postgres.py | — | Delta → Postgres |

## Run

```bash
# Terminal 1 — Kafka
make streaming-up

# Terminal 2 — producer
python -m streaming.producer --rate 5

# Terminal 3 — Spark Bronze writer
make streaming-bronze

# Terminal 4 — Postgres sink
make streaming-postgres

# Terminal 5 — verify
make streaming-status
Kafka UI: http://localhost:8086
Superset: http://localhost:8088

Design decisions
KRaft mode — Kafka 3.7 runs without ZooKeeper. One container instead of two.

Delta Lake sink with checkpointing — exactly-once semantics via checkpointLocation. Replays are safe.

startingOffsets=latest — new Spark jobs pick up where they start, not from the beginning. Use earliest for backfills.

Basic validation in the stream — drop rows with null event_id/order_id or negative sales before writing.

10-second micro-batch — balance between latency and throughput on a laptop.

Partitioned Bronze by category — matches the batch Bronze layer.

Postgres primary key on event_id — makes the append idempotent even if a batch is retried.

Metrics to watch in Grafana
openbi_stream_bronze_rows — total events processed

openbi_stream_ingest_rate — events per second (rate over 1m)

openbi_stream_lag_seconds — difference between now() and max(event_time)

(Extend src/openbi/metrics/exporter.py to expose these — see the file.)

Stopping
bash
# Ctrl+C in each terminal running a Spark query
make streaming-down
