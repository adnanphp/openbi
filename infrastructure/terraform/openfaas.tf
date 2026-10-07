# OpenFaaS Community Edition.
#
# Installed via Helm (not arkade — newer arkade defaults to OpenFaaS Pro,
# which requires a license). The gateway is exposed through Traefik via
# a separate IngressRoute applied by kubectl_manifest.

resource "kubernetes_namespace" "openfaas" {
  metadata {
    name = "openfaas"
    labels = {
      "app.kubernetes.io/name"    = "openfaas"
      "app.kubernetes.io/part-of" = "openbi-platform"
    }
  }

  depends_on = [null_resource.wait_for_api]
}

resource "kubernetes_namespace" "openfaas_fn" {
  metadata {
    name = "openfaas-fn"
    labels = {
      "app.kubernetes.io/name"    = "openfaas"
      "app.kubernetes.io/part-of" = "openbi-platform"
    }
  }

  depends_on = [null_resource.wait_for_api]
}

resource "helm_release" "openfaas" {
  name      = "openfaas"
  namespace = kubernetes_namespace.openfaas.metadata[0].name

  repository = "https://openfaas.github.io/faas-netes/"
  chart      = "openfaas"

  set {
    name  = "functionNamespace"
    value = kubernetes_namespace.openfaas_fn.metadata[0].name
  }

  set {
    name  = "generateBasicAuth"
    value = "true"
  }

  set {
    name  = "serviceType"
    value = "ClusterIP"
  }

  depends_on = [
    null_resource.wait_for_api,
    kubernetes_namespace.openfaas,
    kubernetes_namespace.openfaas_fn,
    helm_release.traefik,
  ]
}
