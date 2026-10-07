locals {
  localstack_dir = "${path.module}/../kubernetes/localstack"
}

data "kubectl_file_documents" "localstack_deployment" {
  content = file("${local.localstack_dir}/deployment.yaml")
}

resource "kubectl_manifest" "localstack_deployment" {
  for_each         = data.kubectl_file_documents.localstack_deployment.manifests
  yaml_body        = each.value
  depends_on       = [kubernetes_namespace.localstack, null_resource.wait_for_api]
  wait_for_rollout = false
}

data "kubectl_file_documents" "localstack_service" {
  content = file("${local.localstack_dir}/service.yaml")
}

resource "kubectl_manifest" "localstack_service" {
  for_each         = data.kubectl_file_documents.localstack_service.manifests
  yaml_body        = each.value
  depends_on       = [kubectl_manifest.localstack_deployment]
  wait_for_rollout = false
}

data "kubectl_file_documents" "localstack_ingress" {
  content = file("${local.localstack_dir}/ingress-routes.yaml")
}

resource "kubectl_manifest" "localstack_ingress" {
  for_each         = data.kubectl_file_documents.localstack_ingress.manifests
  yaml_body        = each.value
  depends_on       = [kubectl_manifest.localstack_service]
  wait_for_rollout = false
}
