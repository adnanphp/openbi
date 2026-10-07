# OpenBI — Cloud Mapping

OpenBI runs as a fully local data platform. Every component in the stack
maps to a managed service in AWS or GCP. This document is the index of
those mappings, so the platform's *cloud-transferable* architecture is
explicit rather than implied.

**Why this matters:** the individual components (ingress, cache, queue,
object storage) can be learned from any tutorial. The value of OpenBI's
cloud-readiness work is learning them **in a system that looks like the
one you'd deploy to AWS or GCP**, at zero cost, with real SDK code.

---

## Executive summary

The v3.0.0 work adds a cloud-readiness layer to the existing OpenBI
platform. Every service is chosen because it speaks the same protocol as
its managed counterpart:

- **Ingress** — Traefik (host-based routing) ↔ AWS ALB / GCP Cloud LB
- **Object storage** — MinIO and LocalStack S3 (S3 protocol) ↔ Amazon S3 / GCS
- **Cache** — Redis (cache-aside pattern) ↔ ElastiCache / Memorystore
- **Messaging** — SQS via LocalStack (queue semantics) ↔ Amazon SQS / Cloud Tasks
- **Serverless** — OpenFaaS (functions as pods) ↔ Lambda / Cloud Functions
- **Logging** — Loki (label-based, LogQL queries) ↔ CloudWatch Logs / Cloud Logging
- **Infrastructure as code** — Terraform (reproducible from zero) ↔ same

The `boto3` code written against LocalStack runs unchanged against real
AWS. The Traefik and Loki configs transfer in concept but not syntax.
The Terraform modules are the same pattern; only the provider and cluster
resource change.

**Skill signal:** the platform demonstrates the full stack of production
concerns — networking, storage, caching, messaging, serverless,
observability, IaC — not as isolated tutorials, but as a working system
that can be destroyed and rebuilt with `terraform apply`.

---

## The mapping at a glance

| OpenBI component       | AWS                                    | GCP                                    | Doc                                   |
| ---------------------- | -------------------------------------- | -------------------------------------- | ------------------------------------- |
| Traefik ingress        | Application Load Balancer (ALB)        | Cloud Load Balancing                   | [networking.md](networking.md)        |
| MinIO (S3 API)         | Amazon S3                              | Cloud Storage                          | [storage.md](storage.md)              |
| Redis                  | ElastiCache for Redis                  | Memorystore for Redis                  | [caching.md](caching.md)              |
| LocalStack S3          | Amazon S3 (via AWS SDK)                | Cloud Storage                          | [localstack.md](localstack.md)        |
| LocalStack SQS         | Amazon SQS                             | Cloud Tasks / Pub/Sub                  | [localstack.md](localstack.md)        |
| OpenFaaS               | AWS Lambda                             | Cloud Functions                        | [serverless.md](serverless.md)        |
| Loki                   | CloudWatch Logs                        | Cloud Logging                          | [logging.md](logging.md)              |
| PostgreSQL             | RDS for PostgreSQL                     | Cloud SQL for PostgreSQL               | [../README.md](../README.md#-data-warehouse) |
| Kafka                  | Amazon MSK                             | Pub/Sub (with caveats)                 | [../README.md](../README.md#real-time-streaming) |
| Spark + Delta Lake     | EMR / Glue                             | Dataproc                               | [architecture_bigdata.md](architecture_bigdata.md) |
| dbt                    | Glue DataBrew / dbt Cloud              | Dataform                               | [dbt.md](dbt.md)                      |
| Airflow                | MWAA                                   | Cloud Composer                         | [../README.md](../README.md#-technology-stack) |
| Superset               | Amazon QuickSight / Managed Grafana    | Looker Studio / Managed Grafana        | [../README.md](../README.md#-dashboards) |
| FastAPI                | ECS Fargate / App Runner               | Cloud Run                              | [../README.md](../README.md#-fastapi-service) |
| Prometheus + Grafana   | Amazon Managed Prometheus / Managed Grafana | Google Cloud Managed Service for Prometheus | [monitoring.md](monitoring.md)        |
| Docker images          | Amazon ECR                             | Artifact Registry                      | [../README.md](../README.md#cicd)     |
| Kind Kubernetes        | Amazon EKS                             | Google Kubernetes Engine (GKE)         | [terraform.md](terraform.md)          |
| Terraform              | Terraform AWS provider                 | Terraform Google provider              | [terraform.md](terraform.md)          |
| GitHub Actions         | CodeBuild / CodePipeline               | Cloud Build                            | [../README.md](../README.md#cicd)     |

---

## How to read this document

Each row is not a claim of equivalence. It's a claim of **conceptual
transfer**. Specifically:

- **The SDK is often the same.** `boto3` works against LocalStack S3 and
  real AWS S3 with the same code — only `endpoint_url` and credentials
  change.
- **The API is often the same.** The S3 protocol is the S3 protocol,
  whether it's MinIO, LocalStack, or AWS. Requests, headers, signatures,
  and errors match.
- **The concepts are always the same.** Host-based routing, TTLs,
  queue semantics, bucket policies — these are the conceptual layer that
  survives every provider change.

The full "what transfers / what doesn't" detail lives in each linked doc.

---

## The three layers of transferability

**Layer 1 — SDK code.** This code is byte-for-byte identical between
LocalStack and AWS:

```python
import boto3

# The one-line change from local to cloud:
#   endpoint_url = "http://localstack.openbi.local:8080"  (local)
#   endpoint_url omitted                                  (AWS)
s3 = boto3.client(
    "s3",
    endpoint_url="http://localstack.openbi.local:8080",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)
s3.create_bucket(Bucket="openbi-raw")
s3.put_object(Bucket="openbi-raw", Key="hello.txt", Body=b"hi")
Change two lines and the same code runs against real AWS S3.

Layer 2 — Protocol shape. The requests, signatures (SigV4), error
codes, and pagination behave the same. If you debug a LocalStack issue,
you're debugging a real AWS issue.

Layer 3 — Architectural concepts. Host-based routing, cache-aside
pattern, at-least-once queue delivery, object key namespacing. These are
provider-agnostic — they're the reason a data engineer who knows
ElastiCache can pick up Memorystore in a week.

What does NOT transfer
Naming the differences honestly is part of the value:

Aspect	Local	AWS / GCP
Durability	PVC on one node	Multi-AZ replication, 99.999999999%
IAM policy enforcement	Not enforced (LocalStack Community)	Full IAM
Cost model	$0	Pay-per-use (with free tiers)
Cross-region	Not applicable	Fully supported
Autoscaling	Manual replica count	Managed autoscaling
Metrics export	Prometheus / statsd	CloudWatch / Cloud Monitoring
Secrets management	Env vars / K8s Secrets	Secrets Manager / Secret Manager
Certificate management	Manual	ACM / Managed Certificates
Log retention	2 Gi PVC	Configurable, virtually unlimited
Cold start latency	Container startup (~500 ms)	Optimized runtime (~100 ms)
Network latency	Localhost / bridge	Region-dependent, usually 1–20 ms
Each detail doc lists the specifics for its component.

Skills demonstrated by this work
Reading this document, the reader should be able to trace:

Networking — host-based routing, reverse proxy configuration,
ingress controller selection, TLS termination patterns
(networking.md)

Storage — S3 protocol, bucket policies, presigned URLs,
path-style vs virtual-hosted addressing (storage.md,
localstack.md)

Caching — cache-aside pattern, TTL selection, hit/miss
instrumentation, graceful degradation when the cache is down
(caching.md)

Messaging — queue semantics, at-least-once delivery,
long-polling consumers, SQS from the AWS SDK (localstack.md)

Serverless — function-as-a-container, HTTP invocation contract,
scale-to-zero (serverless.md)

Observability — structured JSON logging, correlation IDs
(request_id), log aggregation, LogQL queries (logging.md)

Infrastructure as Code — cluster provisioning, Helm releases,
multi-document YAML handling, readiness gates, destroy-and-rebuild
(terraform.md)

Reproducibility — from an empty Docker host, terraform apply
and one bootstrap script rebuild the entire platform

What would change for real AWS or GCP
This section describes the concrete deltas for deploying the same
architecture on real cloud services.

What stays the same
All application code. The FastAPI service, the cache layer, the
boto3 scripts, the structured logging middleware — unchanged.

All Kubernetes manifests. Namespaces, Deployments, Services,
IngressRoutes — unchanged.

All Helm values. Traefik, OpenFaaS, Loki, Promtail — unchanged
(except for cloud-specific annotations for load balancers).

The Terraform structure. Same providers.tf /
namespaces.tf / kubectl_manifest pattern. Only the cluster
resource changes.

What changes for AWS (EKS)
Cluster provisioning. Replace the tehcyx/kind module with the
terraform-aws-modules/eks/aws module. The Kind-specific
extra_port_mappings becomes an ALB IngressClass annotation.

Kubeconfig retrieval. Replace kind get kubeconfig with
aws eks update-kubeconfig.

Image loading. Replace kind load docker-image with pushing to
ECR and referencing ECR URLs in the manifests.

Ingress. Traefik still works, but you'd typically switch to the
AWS Load Balancer Controller and use standard Kubernetes
Ingress resources — ALB is provisioned automatically.

Secrets. Move from Kubernetes Secrets to AWS Secrets Manager
(referenced via External Secrets Operator or CSI driver).

Logging. Point Promtail at CloudWatch Logs instead of Loki, or
use Fluent Bit as the DaemonSet.

Storage. Replace PVCs with EBS volumes (via the EBS CSI driver).
Replace MinIO with real S3 for objects.

What changes for GCP (GKE)
The same seven changes, mapped to GCP equivalents:

terraform-google-modules/kubernetes-engine/google for the cluster

gcloud container clusters get-credentials

Artifact Registry for images

GKE Ingress with Google-managed certificates

Secret Manager

Cloud Logging (Fluent Bit ships logs natively)

PD-SSD for volumes, GCS for objects

What you'd learn by doing it
The deltas above are the entire remaining gap between this lab and a
real cloud deployment. Each one is a bounded task. Combined, they'd take
2–3 weeks of focused work — not because the concepts are hard (they
aren't; they're the same concepts demonstrated here), but because each
service has its own IAM, networking, and cost-management surface.

Verifying this yourself
The following commands verify that each layer is actually working. No
credentials needed — everything runs locally.

bash
# 1. Full platform is reproducible
cd infrastructure/terraform
terraform destroy
terraform apply              # ~3 minutes
./scripts/bootstrap-kind-images.sh

# 2. Every service is reachable via URL
curl -s http://api.openbi.local:8080/health              # {"status":"OK"}
curl -s http://api.openbi.local:8080/cache/stats | jq
curl -s -o /dev/null -w "%{http_code}\n" http://s3.openbi.local:8080/minio/health/live
curl -s -o /dev/null -w "%{http_code}\n" http://localstack.openbi.local:8080/_localstack/health
curl -s -o /dev/null -w "%{http_code}\n" http://faas.openbi.local:8080/system/info

# 3. boto3 works against LocalStack (the AWS SDK transferability claim)
python scripts/localstack_aws_test.py

# 4. Structured logs are being shipped to Loki
kubectl --context kind-openbi port-forward -n logging svc/loki-gateway 3100:80 &
sleep 2
START_NS=$(date -d '5 minutes ago' +%s)000000000
END_NS=$(date +%s)000000000
curl -sG 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={namespace="openbi", app="fastapi"}' \
  --data-urlencode "start=${START_NS}" \
  --data-urlencode "end=${END_NS}" \
  --data-urlencode 'limit=3' | jq '.data.result[0].values'

# 5. Every IngressRoute is active
curl -s http://traefik.openbi.local:8080/api/rawdata | jq '.routers | keys'
If any of these fail, the linked doc has the specific debugging steps.

Roadmap
This document grew as v3.0.0 progressed. All eight phases complete:

✅ Phase 1 — Traefik ingress → ALB / Cloud LB

✅ Phase 2 — MinIO → S3 / GCS

✅ Phase 3 — Redis → ElastiCache / Memorystore

✅ Phase 4 — LocalStack (S3 + SQS) → S3 + SQS

✅ Phase 5 — OpenFaaS serverless → Lambda / Cloud Functions

✅ Phase 6 — Terraform refactor → Terraform AWS/GCP providers

✅ Phase 7 — Loki + structured logging → CloudWatch Logs / Cloud Logging

✅ Phase 8 — This document

Related documents
v3-roadmap.md — the phased plan

networking.md — Traefik, host-based routing

storage.md — MinIO S3-compatible object storage

caching.md — Redis cache-aside pattern

localstack.md — AWS SDK against LocalStack

serverless.md — OpenFaaS functions

terraform.md — Infrastructure as Code

logging.md — Loki + structured JSON logs

../README.md — the main platform README
