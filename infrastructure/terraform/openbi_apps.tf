locals {
  openbi_dir = "${path.module}/../kubernetes"
}

# ---- Postgres ----
data "kubectl_file_documents" "postgres" {
  content = file("${local.openbi_dir}/postgres-deployment.yaml")
}

resource "kubectl_manifest" "postgres" {
  for_each         = data.kubectl_file_documents.postgres.manifests
  yaml_body        = each.value
  depends_on       = [kubernetes_namespace.openbi, null_resource.wait_for_api]
  wait_for_rollout = false
}

# ---- FastAPI ----
data "kubectl_file_documents" "fastapi" {
  content = file("${local.openbi_dir}/fastapi-deployment.yaml")
}

resource "kubectl_manifest" "fastapi" {
  for_each         = data.kubectl_file_documents.fastapi.manifests
  yaml_body        = each.value
  depends_on       = [kubectl_manifest.postgres]
  wait_for_rollout = false
}

# ---- Superset ----
data "kubectl_file_documents" "superset" {
  content = file("${local.openbi_dir}/superset-deployment.yaml")
}

resource "kubectl_manifest" "superset" {
  for_each         = data.kubectl_file_documents.superset.manifests
  yaml_body        = each.value
  depends_on       = [kubectl_manifest.postgres]
  wait_for_rollout = false
}

# ---- OpenBI IngressRoutes ----
data "kubectl_file_documents" "openbi_ingress" {
  content = file("${local.openbi_dir}/ingress-routes.yaml")
}

resource "kubectl_manifest" "openbi_ingress" {
  for_each         = data.kubectl_file_documents.openbi_ingress.manifests
  yaml_body        = each.value
  depends_on       = [kubectl_manifest.fastapi, kubectl_manifest.superset]
  wait_for_rollout = false
}

# ---- OpenFaaS gateway IngressRoute ----
data "kubectl_file_documents" "openfaas_ingress" {
  content = file("${local.openbi_dir}/openfaas/ingress-routes.yaml")
}

resource "kubectl_manifest" "openfaas_ingress" {
  for_each         = data.kubectl_file_documents.openfaas_ingress.manifests
  yaml_body        = each.value
  depends_on       = [helm_release.openfaas]
  wait_for_rollout = false
}
