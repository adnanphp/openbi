# OpenBI application services: Postgres, FastAPI, Superset.
#
# Manifests live in infrastructure/kubernetes/ (flat, at the top level).

locals {
  openbi_dir = "${path.module}/../kubernetes"
}

resource "kubectl_manifest" "openbi_postgres" {
  yaml_body = file("${local.openbi_dir}/postgres-deployment.yaml")

  depends_on = [
    kubernetes_namespace.openbi,
    null_resource.wait_for_api,
  ]

  wait_for_rollout = false
}

resource "kubectl_manifest" "openbi_fastapi" {
  yaml_body = file("${local.openbi_dir}/fastapi-deployment.yaml")

  depends_on = [kubectl_manifest.openbi_postgres]

  wait_for_rollout = false
}

resource "kubectl_manifest" "openbi_superset" {
  yaml_body = file("${local.openbi_dir}/superset-deployment.yaml")

  depends_on = [kubectl_manifest.openbi_postgres]

  wait_for_rollout = false
}

resource "kubectl_manifest" "openbi_ingress" {
  yaml_body = file("${local.openbi_dir}/ingress-routes.yaml")

  depends_on = [
    kubectl_manifest.openbi_fastapi,
    kubectl_manifest.openbi_superset,
  ]

  wait_for_rollout = false
}

resource "kubectl_manifest" "openfaas_ingress" {
  yaml_body = file("${path.module}/../kubernetes/openfaas/ingress-routes.yaml")

  depends_on = [helm_release.openfaas]

  wait_for_rollout = false
}
