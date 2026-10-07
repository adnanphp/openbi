# LocalStack — AWS API emulation (S3, SQS).
#
# Manifests live in infrastructure/kubernetes/localstack/.

locals {
  localstack_dir = "${path.module}/../kubernetes/localstack"
}

resource "kubectl_manifest" "localstack_deployment" {
  yaml_body = file("${local.localstack_dir}/deployment.yaml")

  depends_on = [
    kubernetes_namespace.localstack,
    null_resource.wait_for_api,
  ]

  wait_for_rollout = false
}

resource "kubectl_manifest" "localstack_service" {
  yaml_body = file("${local.localstack_dir}/service.yaml")

  depends_on = [kubectl_manifest.localstack_deployment]

  wait_for_rollout = false
}

resource "kubectl_manifest" "localstack_ingress" {
  yaml_body = file("${local.localstack_dir}/ingress-routes.yaml")

  depends_on = [kubectl_manifest.localstack_service]

  wait_for_rollout = false
}
