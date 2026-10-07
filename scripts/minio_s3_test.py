"""Smoke test: boto3 against MinIO's S3-compatible API.

The code here is identical to what you'd write against real AWS S3.
Only the endpoint_url and credentials differ.
"""

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

ENDPOINT = "http://s3.openbi.local:8080"
AWS_ACCESS_KEY = "minioadmin"
AWS_SECRET_KEY = "minioadmin"
REGION = "us-east-1"


def make_client():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        region_name=REGION,
    )


def main():
    s3 = make_client()
    buckets = ["openbi-raw", "openbi-processed", "openbi-models"]

    # 1. Create buckets
    for name in buckets:
        try:
            s3.create_bucket(Bucket=name)
            print(f"Created bucket: {name}")
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                print(f"Bucket already exists: {name}")
            else:
                raise

    # 2. Upload an object
    key = "samples/hello.txt"
    body = b"Hello from boto3 + MinIO S3\n"
    s3.put_object(Bucket="openbi-raw", Key=key, Body=body)
    print(f"Uploaded: s3://openbi-raw/{key}")

    # 3. List objects
    resp = s3.list_objects_v2(Bucket="openbi-raw")
    print("Objects in openbi-raw:")
    for obj in resp.get("Contents", []):
        print(f"  - {obj['Key']} ({obj['Size']} bytes)")

    # 4. Download
    obj = s3.get_object(Bucket="openbi-raw", Key=key)
    print(f"Downloaded: {obj['Body'].read().decode().strip()}")

    # 5. Presigned URL
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": "openbi-raw", "Key": key},
        ExpiresIn=3600,
    )
    print(f"Presigned URL (1h): {url}")

    # 6. Cleanup
    for name in buckets:
        resp = s3.list_objects_v2(Bucket=name)
        for obj in resp.get("Contents", []):
            s3.delete_object(Bucket=name, Key=obj["Key"])
        s3.delete_bucket(Bucket=name)
        print(f"Deleted bucket: {name}")


if __name__ == "__main__":
    main()
