#!/usr/bin/env bash
# AWS CLI examples against LocalStack.
#
# These are the exact commands you'd run against real AWS — only the
# AWS_ENDPOINT_URL differs. Unset it (or set it to a real region's URL)
# and provide real credentials, and the same commands work against AWS.

set -euo pipefail

# LocalStack configuration
export AWS_ENDPOINT_URL="http://localstack.openbi.local:8080"
export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"
export AWS_DEFAULT_REGION="us-east-1"

echo "==> S3 operations"
aws s3 mb s3://openbi-cli-demo
aws s3 ls
echo "hello from the aws cli" > /tmp/cli-demo.txt
aws s3 cp /tmp/cli-demo.txt s3://openbi-cli-demo/
aws s3 ls s3://openbi-cli-demo/
aws s3 cp s3://openbi-cli-demo/cli-demo.txt -
aws s3 rm s3://openbi-cli-demo/cli-demo.txt
aws s3 rb s3://openbi-cli-demo

echo
echo "==> SQS operations"
QUEUE_URL=$(aws sqs create-queue --queue-name openbi-cli-demo --query QueueUrl --output text)
echo "Queue URL: ${QUEUE_URL}"

aws sqs send-message \
  --queue-url "${QUEUE_URL}" \
  --message-body '{"event": "cli_test", "value": 42}'

aws sqs receive-message \
  --queue-url "${QUEUE_URL}" \
  --max-number-of-messages 1 | python -m json.tool

aws sqs get-queue-attributes \
  --queue-url "${QUEUE_URL}" \
  --attribute-names ApproximateNumberOfMessages

aws sqs delete-queue --queue-url "${QUEUE_URL}"

echo
echo "==> Done"
