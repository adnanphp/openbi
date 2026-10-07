# MinIO — S3-compatible object storage.
#
# Uses kubectl_file_documents to split multi-document YAML files so each
# document becomes its own Terraform-managed resource.

locals {
  minio_dir = "${path.module}/../kubernetes/minio"
}

data "kubectl_file_documents" "minio_pvc" {
  content = file("${local.minio_dir}/pvc.yaml")
}

resource "kubectl_manifest" "minio_pvc" {
  for_each         = data.kubectl_file_documents.minio_pvc.manifests
  yaml_body        = each.value
  depends_on       = [kubernetes_namespace.minio, null_resource.wait_for_api]
  wait_for_rollout = false
}

data "kubectl_file_documents" "minio_deployment" {
  content = file("${local.minio_dir}/deployment.yaml")
}

resource "kubectl_manifest" "minio_deployment" {
  for_each         = data.kubectl_file_documents.minio_deployment.manifests
  yaml_body        = each.value
  depends_on       = [kubectl_manifest.minio_pvc]
  wait_for_rollout = false
}

data "kubectl_file_documents" "minio_service" {
  content = file("${local.minio_dir}/service.yaml")
}

resource "kubectl_manifest" "minio_service" {
  for_each         = data.kubectl_file_documents.minio_service.manifests
  yaml_body        = each.value
  depends_on       = [kubectl_manifest.minio_deployment]
  wait_for_rollout = false
}

data "kubectl_file_documents" "minio_ingress" {
  content = file("${local.minio_dir}/ingress-routes.yaml")
}

resource "kubectl_manifest" "minio_ingress" {
  for_each         = data.kubectl_file_documents.minio_ingress.manifests
  yaml_body        = each.value
  depends_on       = [kubectl_manifest.minio_service]
  wait_for_rollout = false
}
