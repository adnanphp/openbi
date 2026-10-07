# Object Storage — MinIO (S3-compatible)

OpenBI uses **MinIO** as its local object storage layer. MinIO speaks the
S3 API, so the `boto3` code written against it runs unchanged against
real AWS S3 (only `endpoint_url` and credentials change).

## Why MinIO (and where the image comes from)

The MinIO project removed its official Docker Hub images in late 2025
and now distributes only source code. The OpenBI lab uses a
**community-maintained build** at `ghcr.io/netvark/minio` — a
reproducible image built from the archived source.

This dependency is called out explicitly because it is a real
operational concern. If the community mirror disappears, the swap
target is one of:

- **Garage** — actively maintained, Rust-based, ~50 MB image, full S3 API
- **SeaweedFS** — used by Apache Flink's own S3 tests
- **LocalStack S3** — local AWS S3 emulation (also in the v3 roadmap)

Because the application code uses only `boto3` and standard S3 semantics,
swapping the underlying store requires no application changes — only a
new `endpoint_url`.

## Architecture
boto3 (Python) | aws CLI | Spark
│
│ S3 API (HTTP)
▼
Traefik (ingress)
│
├── Host: minio.openbi.local ──► :9001 (console)
└── Host: s3.openbi.local ──► :9000 (S3 API)
│
▼
MinIO Service (ClusterIP)
│
▼
MinIO Pod
│
▼
PVC (5 Gi) → local-path-provisioner → Kind node disk

text

## Buckets

OpenBI uses three logical buckets:

| Bucket             | Purpose                                        |
| ------------------ | ---------------------------------------------- |
| `openbi-raw`       | Landing zone for raw CSVs, JSON, event dumps   |
| `openbi-processed` | Parquet, cleaned data, intermediate outputs    |
| `openbi-models`    | Trained ML artifacts, model comparison reports |

The naming is a convention, not an enforced schema. Any bucket the
pipeline needs can be created with `boto3` or the MinIO console.

## Connecting with boto3

```python
import boto3
from botocore.client import Config

s3 = boto3.client(
    "s3",
    endpoint_url="http://s3.openbi.local:8080",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin",
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    region_name="us-east-1",
)

s3.create_bucket(Bucket="openbi-raw")
s3.upload_file("data/raw/sample.csv", "openbi-raw", "samples/sample.csv")
To target real AWS S3, remove endpoint_url and use real IAM
credentials. The rest of the code is unchanged.

Connecting with the AWS CLI
bash
export AWS_ENDPOINT_URL="http://s3.openbi.local:8080"
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
export AWS_DEFAULT_REGION=us-east-1

aws s3 ls
aws s3 mb s3://openbi-raw
aws s3 cp data/raw/sample.csv s3://openbi-raw/
Accessing the console
Browser: http://minio.openbi.local:8080

Default credentials (local development only): minioadmin / minioadmin

Loading the image into Kind
Because the MinIO image is not on Docker Hub anymore, first-time setup
requires pulling and loading:

bash
docker pull ghcr.io/netvark/minio:latest
kind load docker-image ghcr.io/netvark/minio:latest --name openbi
Then apply:

bash
kubectl apply -k infrastructure/kubernetes/minio
Cloud mapping
Local	AWS	GCP
MinIO S3 API	Amazon S3	Cloud Storage
bucket	bucket	bucket
object key	object key	object name
boto3.client("s3")	same	google-cloud-storage
presigned URL (SigV4)	presigned URL (SigV4)	signed URL (V4 signing)
path-style addressing	supported (legacy)	not supported
self-hosted	fully managed	fully managed
5 Gi PVC	virtually unlimited	virtually unlimited
Kind node disk	S3-managed, replicated	GCS-managed, replicated
What transfers:

The entire boto3 S3 client API surface

Bucket / object / key / prefix model

Presigned URL mechanics and the SigV4 signing protocol

Multipart uploads

Bucket policies, ACLs, versioning (concept and API)

Server-side encryption configuration

Path-style vs virtual-hosted addressing

What does not transfer:

Durability guarantees (99.999999999% on AWS — MinIO on a Kind PVC
has no such guarantee)

IAM policy enforcement (MinIO has its own IAM model, similar but not
identical to AWS IAM)

Cross-region replication

Storage classes and lifecycle transitions (S3 has many; MinIO has
fewer)

Pricing model
