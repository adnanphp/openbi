# Redis — in-cluster cache.
#
# Manifests live in infrastructure/kubernetes/redis/.

locals {
  redis_dir = "${path.module}/../kubernetes/redis"
}

resource "kubectl_manifest" "redis_pvc" {
  yaml_body = file("${local.redis_dir}/pvc.yaml")

  depends_on = [
    kubernetes_namespace.redis,
    null_resource.wait_for_api,
  ]

  wait_for_rollout = false
}

resource "kubectl_manifest" "redis_deployment" {
  yaml_body = file("${local.redis_dir}/deployment.yaml")

  depends_on = [kubectl_manifest.redis_pvc]

  wait_for_rollout = false
}

resource "kubectl_manifest" "redis_service" {
  yaml_body = file("${local.redis_dir}/service.yaml")

  depends_on = [kubectl_manifest.redis_deployment]

  wait_for_rollout = false
}
