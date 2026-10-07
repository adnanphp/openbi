"""End-to-end demonstration of S3 + SQS against LocalStack.

This script uses boto3, the same AWS SDK that works against real AWS.
The only differences for real AWS are:
  - Remove endpoint_url (boto3 defaults to AWS endpoints)
  - Use real AWS access key / secret key
  - Use the actual AWS region

Demonstrates the pattern that underlies event-driven pipelines:
  1. Producer sends an event to an SQS queue
  2. Consumer receives the event
  3. Consumer stores the payload in S3
  4. Downstream reads it back from S3
  5. Cleanup
"""

from __future__ import annotations

import json
import time
import uuid

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

# ----------------------------------------------------------------------
# Configuration — change ONLY these for real AWS.
# ----------------------------------------------------------------------
ENDPOINT = "http://localstack.openbi.local:8080"
AWS_ACCESS_KEY = "test"
AWS_SECRET_KEY = "test"
REGION = "us-east-1"

QUEUE_NAME = "openbi-events"
BUCKET_NAME = "openbi-events-archive"


def make_client(service: str):
    return boto3.client(
        service,
        endpoint_url=ENDPOINT,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        region_name=REGION,
    )


def ensure_bucket(s3, name: str) -> None:
    try:
        s3.create_bucket(Bucket=name)
        print(f"[s3]    Created bucket: {name}")
    except ClientError as exc:
        if exc.response["Error"]["Code"] in (
            "BucketAlreadyOwnedByYou",
            "BucketAlreadyExists",
        ):
            print(f"[s3]    Bucket exists: {name}")
        else:
            raise


def ensure_queue(sqs, name: str) -> str:
    resp = sqs.create_queue(QueueName=name)
    print(f"[sqs]   Queue ready: {resp['QueueUrl']}")
    return resp["QueueUrl"]


def main() -> None:
    s3 = make_client("s3")
    sqs = make_client("sqs")

    print("=" * 60)
    print("OpenBI — LocalStack S3 + SQS integration demo")
    print("=" * 60)

    # 1. Set up resources
    print("\n[SETUP]")
    ensure_bucket(s3, BUCKET_NAME)
    queue_url = ensure_queue(sqs, QUEUE_NAME)

    # 2. Produce three events
    print("\n[PRODUCE]")
    event_ids = []
    for i in range(3):
        event_id = str(uuid.uuid4())
        event_ids.append(event_id)
        payload = {
            "event_id": event_id,
            "event_type": "order.created",
            "order_id": 1000 + i,
            "amount": round(100.0 + i * 25.5, 2),
            "timestamp": time.time(),
        }
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(payload),
        )
        print(f"[sqs]   Sent event {event_id[:8]}… (order_id={payload['order_id']})")

    # 3. Consume events and archive each to S3
    print("\n[CONSUME]")
    archived = 0
    for _ in range(3):
        resp = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=2,
        )
        messages = resp.get("Messages", [])
        if not messages:
            print("[sqs]   No messages available")
            break

        msg = messages[0]
        body = msg["Body"]
        payload = json.loads(body)
        event_id = payload["event_id"]

        # Archive to S3
        key = f"events/{event_id}.json"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
        )
        print(f"[s3]    Archived {key}")

        # Ack the message
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=msg["ReceiptHandle"],
        )
        archived += 1

    # 4. List what's in S3
    print("\n[VERIFY]")
    resp = s3.list_objects_v2(Bucket=BUCKET_NAME)
    objects = resp.get("Contents", [])
    print(f"[s3]    {len(objects)} objects in s3://{BUCKET_NAME}/")
    for obj in objects[:5]:
        print(f"        - {obj['Key']} ({obj['Size']} bytes)")

    # 5. Read one object back
    if objects:
        sample_key = objects[0]["Key"]
        body = s3.get_object(Bucket=BUCKET_NAME, Key=sample_key)["Body"].read()
        payload = json.loads(body)
        print(f"[s3]    Sample: {sample_key}")
        print(f"        event_type={payload['event_type']} "
              f"order_id={payload['order_id']} amount=${payload['amount']}")

    # 6. Queue should now be empty
    attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=["ApproximateNumberOfMessages"],
    )
    remaining = attrs["Attributes"]["ApproximateNumberOfMessages"]
    print(f"\n[sqs]   Messages remaining in queue: {remaining}")

    # 7. Cleanup
    print("\n[CLEANUP]")
    for obj in objects:
        s3.delete_object(Bucket=BUCKET_NAME, Key=obj["Key"])
    s3.delete_bucket(Bucket=BUCKET_NAME)
    print(f"[s3]    Deleted bucket {BUCKET_NAME}")

    sqs.delete_queue(QueueUrl=queue_url)
    print(f"[sqs]   Deleted queue {QUEUE_NAME}")

    print("\n" + "=" * 60)
    print(f"DONE — {archived} events archived and cleaned up")
    print("=" * 60)


if __name__ == "__main__":
    main()
