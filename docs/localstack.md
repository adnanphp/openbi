# LocalStack — AWS API Emulation

OpenBI runs **LocalStack** as an in-cluster emulator of AWS APIs. This
lets the same `boto3` code run locally against a local endpoint and
against real AWS without changes — the pattern that gives the
project's storage and messaging layers their AWS-transferable shape.

## Why LocalStack

The 2023–2025 MinIO licensing and distribution changes demonstrated that
self-hosted dependencies can shift underfoot. LocalStack fills the gap by
emulating the *exact* AWS APIs — not a subset, not a compatible surface,
but the real AWS protocol as exercised by the real AWS SDK.

If the specific service behavior matters (IAM policy evaluation, error
codes, pagination, retry semantics), LocalStack provides it. MinIO and
Garage provide S3 *compatibility*; LocalStack provides S3 *the way AWS
does it*.

## Architecture
boto3 (Python) aws (CLI)
│ │
└───────────┬───────────┘
│
│ AWS HTTP API
▼
Traefik (ingress)
│
│ Host: localstack.openbi.local
▼
LocalStack Service (ClusterIP)
│
│ :4566
▼
LocalStack Pod
│
├── S3 buckets / objects
└── SQS queues / messages

text

## Enabled services

`SERVICES=s3,sqs` in the deployment. LocalStack lazily starts services
on first use. Adding more services is a one-line env var change and a
pod restart.

| Service | Status |
| --- | --- |
| S3 | enabled |
| SQS | enabled |
| Lambda | disabled (deliberately out of scope — Docker-in-Docker complexity) |
| DynamoDB | disabled |
| IAM | disabled (LocalStack Community doesn't enforce IAM by default) |

## Connecting with boto3

```python
import boto3
from botocore.client import Config

# The entire difference from real AWS:
#   - endpoint_url     → LocalStack URL (or omitted for real AWS)
#   - access key/secret → LocalStack dummy creds (or real IAM creds)
sqs = boto3.client(
    "sqs",
    endpoint_url="http://localstack.openbi.local:8080",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
    config=Config(signature_version="s3v4"),
)

queue = sqs.create_queue(QueueName="openbi-events")
sqs.send_message(QueueUrl=queue["QueueUrl"], MessageBody='{"x": 1}')
Connecting with the AWS CLI
bash
export AWS_ENDPOINT_URL="http://localstack.openbi.local:8080"
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

aws s3 ls
aws s3 mb s3://openbi-demo
aws sqs create-queue --queue-name openbi-events
The only difference from a real AWS session is AWS_ENDPOINT_URL.
Unset it, provide real credentials, and the same commands hit AWS.

Demonstrations
Script	Purpose
scripts/minio_s3_test.py	S3-only smoke test against MinIO (Phase 2)
scripts/localstack_aws_test.py	Combined S3 + SQS pipeline (Phase 4)
scripts/aws_cli_examples.sh	Same operations via the aws CLI
Persistence caveat
LocalStack Community Edition does not persist state across pod
restarts. Buckets, objects, queues, and messages are held in memory.
For a learning environment this is acceptable — the demonstration
scripts recreate everything they need on each run.

Cloud mapping
Local	AWS	GCP
LocalStack S3	Amazon S3	Cloud Storage
LocalStack SQS	Amazon SQS	Cloud Tasks / Pub/Sub (with caveats)
boto3 SDK	same library, same API	google-cloud-* (different API)
aws CLI	same CLI	gcloud CLI
dummy creds test/test	IAM access keys	service account keys
LocalStack endpoint URL	region endpoint	regional endpoint
in-memory (no persistence)	durable, replicated	durable, replicated
What transfers directly:

The entire boto3 client API surface

The aws CLI command surface

Error codes and exceptions (ClientError with .response["Error"])

Pagination patterns (get_paginator)

Waiters, retries, and timeouts

Signature V4 request signing

What does not transfer:

IAM policy enforcement (LocalStack Community doesn't enforce by default)

Cross-region replication

Service quotas and rate limits

Pricing model

Availability zone concepts

Real durability SLAs

Verification
bash
# Health
curl -s http://localstack.openbi.local:8080/_localstack/health | jq '.services | to_entries | map(select(.value != "disabled"))'
Design notes
Why SQS and not SNS or Kinesis?

SQS is the simplest AWS messaging primitive and the most commonly used
in production pipelines. SNS (pub/sub fan-out) and Kinesis (streaming)
are valuable but add complexity without teaching new fundamentals. The
OpenBI platform already covers streaming with Kafka (v2.x) and SQS
demonstrates queue semantics alongside it.

Why not Lambda?

Lambda emulation in LocalStack Community requires Docker-in-Docker or a
runner sidecar, and introduces cold-start, concurrency, and IAM
complexity that isn't directly relevant to the OpenBI use case. Lambda
is documented here as a future addition but not included in the current
implementation.
