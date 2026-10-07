# Caching — Redis

OpenBI uses **Redis** as an in-cluster cache for expensive read endpoints.
The cache follows the cache-aside pattern: check Redis first, fall back
to Postgres on miss, populate Redis on the way out.

## Architecture
Client → Traefik → FastAPI
│
├─ cache_get(key)
│ │
│ ├─ HIT → return cached JSON
│ │
│ └─ MISS → query Postgres
│ │
│ ▼
│ cache_set(key, value, ttl)
│ │
│ ▼
└────── return response

text

## Cached endpoints

| Endpoint | Cache key | TTL | Reason |
| --- | --- | --- | --- |
| `GET /kpis/executive` | `openbi:kpis:executive` | 300 s | Heavy aggregation over `fact_sales` |
| `GET /kpis/monthly-revenue` | `openbi:kpis:monthly_revenue` | 300 s | 48-month rollup |
| `GET /kpis/by-category` | `openbi:kpis:by_category` | 300 s | Grouped aggregation |
| `GET /customers/segments` | `openbi:customers:segments` | 600 s | ML output; changes only on retrain |
| `GET /forecasts/latest` | `openbi:forecasts:latest` | 600 s | ML output |
| `GET /forecasts/models` | `openbi:forecasts:models` | 600 s | ML output |

## Not cached

| Endpoint | Reason |
| --- | --- |
| `GET /health` | Must always reflect live process state |
| `GET /cache/stats` | Must always return current hit/miss counters |

## Configuration

The API reads these environment variables at startup:

| Variable | Default | Purpose |
| --- | --- | --- |
| `REDIS_HOST` | `redis.redis.svc.cluster.local` | Redis service DNS |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis database index |

## Cache statistics

```bash
curl -s http://api.openbi.local:8080/cache/stats | jq
Returns:

json
{
  "connected": true,
  "hits": 12,
  "misses": 3,
  "hit_rate": 0.8,
  "keys": 4,
  "host": "redis.redis.svc.cluster.local:6379"
}
Redis deployment
Redis runs in the redis namespace as a single-replica Deployment with a
1 Gi PVC. Configuration:

Setting	Value	Purpose
--appendonly yes	enabled	Persist to disk
--maxmemory 256mb	256 MB cap	Prevent runaway memory use
--maxmemory-policy allkeys-lru	LRU eviction	Standard production policy
The image is redis:7-alpine, ~30 MB.

Graceful degradation
If Redis is unreachable, the API continues to work without caching:

cache_get returns None

The route falls through to Postgres

cache_set fails silently

Response is returned normally, just slower

This is the correct failure mode for a cache: an optimization, not a
dependency. If the API crashed whenever Redis was down, caching would
make the system less reliable, not more.

What transfers to AWS / GCP
Local	AWS	GCP
Redis 7 (self-hosted)	ElastiCache for Redis	Memorystore for Redis
REDIS_HOST / REDIS_PORT env vars	same pattern	same pattern
redis-py client	same library	same library
Cache-aside pattern	same code	same code
TTL / LRU eviction	configurable, same semantics	configurable, same semantics
256 MB max memory	instance size, elastic	instance size, elastic
What transfers directly:

The entire redis-py client API surface

Cache-aside pattern and TTL semantics

Key naming conventions

Eviction policies (LRU, LFU, etc.)

Pipelining, transactions, pub/sub

What does not transfer:

Persistence guarantees (ElastiCache and Memorystore offer managed
replication and failover; single-node self-hosted does not)

Cluster sharding (ElastiCache has cluster mode; Memorystore has
Redis Cluster)

Metrics and monitoring (ElastiCache publishes to CloudWatch;
Memorystore to Cloud Monitoring)

Pricing model

Verification (partial — 2026-10-07)
The Phase 3 smoke test confirms:

Redis is deployed and running in the Kind cluster

FastAPI connects to Redis on startup (/cache/stats returns
connected: true)

The cache_get path is executed on every cached-endpoint call, as
evidenced by the misses counter incrementing

The misses and hits counters are correctly stored and retrieved

Not yet verified: an actual cache hit. The Kind Postgres does
not yet have the warehouse schema loaded, so every cached endpoint
raises UndefinedTable on the fallback DB query and cache_set is
never reached. Full hit verification requires either seeding the Kind
Postgres or pointing FastAPI at a populated Postgres — both are Phase 6
(Terraform IaC) concerns.

The infrastructure is correct; the missing piece is data, not caching.
