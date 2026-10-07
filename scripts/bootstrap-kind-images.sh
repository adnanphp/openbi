#!/usr/bin/env bash
# Load local Docker images into a Kind cluster.
#
# Terraform creates the cluster and applies all Kubernetes manifests,
# but Kind's containerd is a separate image store from the host's Docker
# daemon. Custom-built images (openbi-fastapi) and community-mirror
# images (ghcr.io/netvark/minio) must be explicitly loaded.
#
# This is the one step IaC cannot express. Terraform has no primitive
# for "load a Docker image into another Docker daemon's containerd."
# The pattern is what real CI does: terraform apply, then a bootstrap
# step for image hydration.
#
# Usage:
#   ./scripts/bootstrap-kind-images.sh [cluster-name]
#
# Run after `terraform apply`. Idempotent — skips already-loaded images.

set -euo pipefail

CLUSTER_NAME="${1:-${CLUSTER_NAME:-openbi}}"
KUBECTL="kubectl --context kind-${CLUSTER_NAME}"

echo "==> Ensuring images exist on host Docker daemon"

if ! docker image inspect openbi-fastapi:latest >/dev/null 2>&1; then
  echo "    Building openbi-fastapi:latest..."
  docker build \
    -t openbi-fastapi:latest \
    -f infrastructure/kubernetes/fastapi-app/Dockerfile \
    .
fi

if ! docker image inspect ghcr.io/netvark/minio:latest >/dev/null 2>&1; then
  echo "    Pulling ghcr.io/netvark/minio:latest..."
  docker pull ghcr.io/netvark/minio:latest
fi

for img in postgres:16-alpine redis:7-alpine apache/superset:3.1.3 localstack/localstack:3.8; do
  if ! docker image inspect "$img" >/dev/null 2>&1; then
    echo "    Pulling $img..."
    docker pull "$img"
  fi
done

echo
echo "==> Loading images into Kind cluster '${CLUSTER_NAME}'"

for img in \
  openbi-fastapi:latest \
  ghcr.io/netvark/minio:latest \
  postgres:16-alpine \
  redis:7-alpine \
  apache/superset:3.1.3 \
  localstack/localstack:3.8
do
  echo "    Loading $img..."
  kind load docker-image "$img" --name "${CLUSTER_NAME}"
done

echo
echo "==> Restarting affected deployments to pick up the loaded images"

for ns_deploy in \
  "openbi/fastapi" \
  "openbi/postgres" \
  "openbi/superset" \
  "minio/minio" \
  "redis/redis" \
  "localstack/localstack"
do
  ns="${ns_deploy%%/*}"
  dep="${ns_deploy##*/}"
  $KUBECTL rollout restart -n "$ns" "deployment/$dep" 2>/dev/null || true
done

echo
echo "==> Done. Pods will take ~30-60s to become ready."
echo "    Watch with: kubectl --context kind-${CLUSTER_NAME} get pods -A"
