# Logging — Loki + Promtail + Structured JSON

OpenBI uses **Loki** for log aggregation and **Promtail** for log
shipping. Application logs are emitted as **structured JSON** on stdout,
scraped by Promtail's DaemonSet, and stored in Loki for querying.

## Why structured JSON logging

The problem with plain-text logs:
INFO: 10.244.1.1:56996 - "GET /health HTTP/1.1" 200 OK

text

Finding all requests that returned 500 requires text parsing. Finding all
requests that took more than 1 second requires a regex. Correlating a
specific request across services requires guesswork.

Structured JSON logs fix all three:

```json
{"level": "INFO", "request_id": "abc123", "method": "GET",
 "path": "/health", "status": 200, "duration_ms": 0.45,
 "client_ip": "172.19.0.1", "timestamp": "2026-10-07T20:52:09Z"}
Finding 500s: {namespace="openbi"} | json | status >= 500.
Finding slow requests: {namespace="openbi"} | json | duration_ms > 1000.
Correlating: search by request_id across every service that logs it.

This is the foundation of production observability.

Architecture
text
FastAPI pods
    │
    │ stdout (JSON lines)
    ▼
Promtail (DaemonSet — one pod per node)
    │
    │ scrapes /var/log/pods/**/*.log
    │ adds Kubernetes labels (namespace, pod, container, node)
    ▼
Loki (single-binary, 2 Gi PVC)
    │
    │ queried via HTTP
    ▼
Grafana (queries Loki as a datasource)
Installation
Loki and Promtail are installed via Terraform (see
infrastructure/terraform/loki.tf). The Helm chart is
grafana/loki in SingleBinary mode with filesystem storage.

bash
cd infrastructure/terraform
terraform apply
The structured logging middleware
src/openbi/api/logging_middleware.py wraps every request:

python
class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        self._log(
            level="INFO",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            client_ip=self._client_ip(request),
        )
        response.headers["X-Request-ID"] = request_id
        return response
Every response carries an X-Request-ID header. Every log line carries
the same value in request_id. This is the correlation primitive.

Querying logs
Loki's query language is LogQL. Examples:

logql
# All logs from the openbi namespace
{namespace="openbi"}

# All FastAPI logs
{namespace="openbi", app="fastapi"}

# Parse JSON and filter by field
{namespace="openbi", app="fastapi"} | json | status >= 500

# Slow requests
{namespace="openbi", app="fastapi"} | json | duration_ms > 100

# Trace a specific request
{namespace="openbi"} | json | request_id = "00619c6c-7246-43ea-8c85-05d0887e3ead"
Connecting Grafana
Compose Grafana (running outside the cluster)
The Compose Grafana cannot reach Loki directly because they're on
different Docker networks. Two options:

Option A — Port-forward (development):

bash
kubectl --context kind-openbi port-forward -n logging svc/loki-gateway 3100:80
Then in Grafana: Connections → Data Sources → Add Loki,
URL = http://host.docker.internal:3100.

Option B — In-cluster Grafana (production-like):

Install Grafana into the Kind cluster via the same Helm chart family:

bash
helm install grafana grafana/grafana -n logging
Then Grafana reaches Loki at http://loki-gateway.logging.svc.cluster.local.

What we did NOT do
Log retention policies: Loki is configured with default retention.
Production would set per-stream retention, compaction, and object
storage backends.

Structured logs from other services: only FastAPI emits JSON so
far. Postgres, Redis, and Superset emit their own log formats. In a
full deployment, you'd either standardize their formats or use
Promtail pipeline stages to parse them.

Log-based alerting: Loki can feed Alertmanager. Not configured
here.

Distributed tracing: OpenTelemetry would be the next layer
(trace_id correlation alongside request_id). Out of scope.

Cloud mapping
Local	AWS	GCP
Loki	CloudWatch Logs	Cloud Logging
Promtail (DaemonSet)	CloudWatch Logs agent / FireLens	Ops Agent / Fluent Bit
LogQL	CloudWatch Logs Insights	Cloud Logging query language
JSON Lines	Same format	Same format
Labels (Kubernetes)	Log group / stream tags	Log labels
Grafana	Managed Grafana / CloudWatch Dashboards	Cloud Monitoring dashboards
2 Gi PVC	Virtually unlimited	Virtually unlimited
What transfers directly:

Structured JSON logging as a pattern

Correlation IDs (request_id) in every log line

Kubernetes labels as log metadata (namespace, pod, container)

Label-based filtering and querying

Retention policies and log levels

The observability use case: debug a specific request, find slow
paths, filter by status code

What does not transfer:

LogQL syntax (CloudWatch Insights and Cloud Logging have their own)

Retention defaults and storage backends

Loki's chunk-based storage format

The kubectl port-forward lab pattern (production uses real DNS
or VPC endpoints)

Verification
bash
# Confirm Promtail is shipping
kubectl --context kind-openbi logs -n logging daemonset/promtail --tail=5

# Confirm Loki has data
curl -s 'http://localhost:3100/loki/api/v1/label/namespace/values'

# Query structured FastAPI logs
START_NS=$(date -d '5 minutes ago' +%s)000000000
END_NS=$(date +%s)000000000
curl -sG 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={namespace="openbi", app="fastapi"}' \
  --data-urlencode "start=${START_NS}" \
  --data-urlencode "end=${END_NS}" \
  --data-urlencode 'limit=5' | python -m json.tool
Expected: JSON logs with request_id, method, path, status,
duration_ms, client_ip, timestamp.
