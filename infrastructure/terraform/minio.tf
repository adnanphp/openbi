# MinIO — S3-compatible object storage.
#
# Manifests live in infrastructure/kubernetes/minio/ and are applied
# through the kubectl provider. Terraform tracks their lifecycle.

locals {
  minio_dir = "${path.module}/../kubernetes/minio"
}

resource "kubectl_manifest" "minio_pvc" {
  yaml_body = file("${local.minio_dir}/pvc.yaml")

  depends_on = [
    kubernetes_namespace.minio,
    null_resource.wait_for_api,
  ]

  wait_for_rollout = false
}

resource "kubectl_manifest" "minio_deployment" {
  yaml_body = file("${local.minio_dir}/deployment.yaml")

  depends_on = [kubectl_manifest.minio_pvc]

  wait_for_rollout = false
}

resource "kubectl_manifest" "minio_service" {
  yaml_body = file("${local.minio_dir}/service.yaml")

  depends_on = [kubectl_manifest.minio_deployment]

  wait_for_rollout = false
}

resource "kubectl_manifest" "minio_ingress" {
  yaml_body = file("${local.minio_dir}/ingress-routes.yaml")

  depends_on = [kubectl_manifest.minio_service]

  wait_for_rollout = false
}
