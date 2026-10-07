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

## The mapping at a glance

| OpenBI component       | AWS                                    | GCP                                    | Doc                                   |
| ---------------------- | -------------------------------------- | -------------------------------------- | ------------------------------------- |
| Traefik ingress        | Application Load Balancer (ALB)        | Cloud Load Balancing                   | [networking.md](networking.md)        |
| MinIO (S3 API)         | Amazon S3                              | Cloud Storage                          | [storage.md](storage.md)              |
| Redis                  | ElastiCache for Redis                  | Memorystore for Redis                  | [caching.md](caching.md)              |
| LocalStack S3          | Amazon S3 (via AWS SDK)                | Cloud Storage                          | [localstack.md](localstack.md)        |
| LocalStack SQS         | Amazon SQS                             | Cloud Tasks / Pub/Sub                  | [localstack.md](localstack.md)        |
| PostgreSQL             | RDS for PostgreSQL                     | Cloud SQL for PostgreSQL               | (v1/v2 platform docs)                 |
| Kafka                  | Amazon MSK                             | Pub/Sub (with caveats)                 | (v2 streaming docs)                   |
| Spark + Delta Lake     | EMR / Glue                             | Dataproc                               | (v2 bigdata docs)                     |
| dbt                    | Glue DataBrew / dbt Cloud              | Dataform                               | (v2 dbt docs)                         |
| Airflow                | MWAA (Managed Workflows for Apache Airflow) | Cloud Composer                    | (v2 orchestration docs)               |
| Superset               | Amazon QuickSight / Managed Grafana    | Looker Studio / Managed Grafana        | (BI docs)                             |
| FastAPI                | ECS Fargate / App Runner               | Cloud Run                              | (API docs)                            |
| Prometheus + Grafana   | Amazon Managed Prometheus / Managed Grafana | Google Cloud Managed Service for Prometheus / Cloud Monitoring | (monitoring docs)                     |
| Docker images          | Amazon ECR                             | Artifact Registry                      | (v2 CI docs)                          |
| Kind Kubernetes        | Amazon EKS                             | Google Kubernetes Engine (GKE)         | (K8s docs)                            |
| Terraform              | Terraform AWS provider                 | Terraform Google provider              | [terraform.md](terraform.md)                |
| GitHub Actions         | CodeBuild / CodePipeline               | Cloud Build                            | (CI docs)                             |

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

The full "what transfers / what doesn't" detail lives in each linked
doc.

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
Each detail doc lists the specifics for its component.

Roadmap
This document grows as v3.0.0 progresses.

☑ Phase 1 — Traefik ingress → ALB / Cloud LB
☑ Phase 2 — MinIO → S3 / GCS
☑ Phase 3 — Redis → ElastiCache / Memorystore
☑ Phase 4 — LocalStack (S3 + SQS) → S3 + SQS
□ Phase 5 — Serverless function → Lambda / Cloud Functions
✅ Phase 6 — Terraform refactor → Terraform AWS/GCP providers
□ Phase 7 — Loki + structured logging → CloudWatch Logs / Cloud Logging
□ Phase 8 — Full mapping doc (this file, completed)
Related documents
v3-roadmap.md — the phased plan

networking.md — Traefik, host routing

storage.md — MinIO S3-compatible object storage

caching.md — Redis cache-aside pattern

localstack.md — AWS SDK against LocalStack
