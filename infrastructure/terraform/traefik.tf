# Traefik ingress controller.
#
# Installed via the official Helm chart. Configuration comes from the
# same values file used by the manual `helm install` command in
# Phase 1, so the two paths stay in sync.

resource "helm_release" "traefik" {
  name             = "traefik"
  namespace        = "traefik"
  create_namespace = true

  repository = "https://traefik.github.io/charts"
  chart      = "traefik"
  version    = "~> 34.0"   # Adjust if a newer major is needed

  values = [
    file("${path.module}/../kubernetes/traefik-values.yaml")
  ]

  depends_on = [null_resource.wait_for_api]
}
