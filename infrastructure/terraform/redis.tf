locals {
  redis_dir = "${path.module}/../kubernetes/redis"
}

data "kubectl_file_documents" "redis_pvc" {
  content = file("${local.redis_dir}/pvc.yaml")
}

resource "kubectl_manifest" "redis_pvc" {
  for_each         = data.kubectl_file_documents.redis_pvc.manifests
  yaml_body        = each.value
  depends_on       = [kubernetes_namespace.redis, null_resource.wait_for_api]
  wait_for_rollout = false
}

data "kubectl_file_documents" "redis_deployment" {
  content = file("${local.redis_dir}/deployment.yaml")
}

resource "kubectl_manifest" "redis_deployment" {
  for_each         = data.kubectl_file_documents.redis_deployment.manifests
  yaml_body        = each.value
  depends_on       = [kubectl_manifest.redis_pvc]
  wait_for_rollout = false
}

data "kubectl_file_documents" "redis_service" {
  content = file("${local.redis_dir}/service.yaml")
}

resource "kubectl_manifest" "redis_service" {
  for_each         = data.kubectl_file_documents.redis_service.manifests
  yaml_body        = each.value
  depends_on       = [kubectl_manifest.redis_deployment]
  wait_for_rollout = false
}
