# Application namespaces.
#
# Using the native kubernetes_namespace resource instead of kubectl_manifest.
# The gavinbunney/kubectl provider fails to discover the Namespace API for
# this resource type on Kind — the hashicorp/kubernetes provider handles
# it natively and reliably.
#
# Traefik and OpenFaaS namespaces are created by their Helm releases
# (via create_namespace = true) and are not listed here.

resource "kubernetes_namespace" "minio" {
  metadata {
    name = "minio"
    labels = {
      "app.kubernetes.io/name"    = "minio"
      "app.kubernetes.io/part-of" = "openbi-platform"
    }
  }

  depends_on = [null_resource.wait_for_api]
}

resource "kubernetes_namespace" "redis" {
  metadata {
    name = "redis"
    labels = {
      "app.kubernetes.io/name"    = "redis"
      "app.kubernetes.io/part-of" = "openbi-platform"
    }
  }

  depends_on = [null_resource.wait_for_api]
}

resource "kubernetes_namespace" "localstack" {
  metadata {
    name = "localstack"
    labels = {
      "app.kubernetes.io/name"    = "localstack"
      "app.kubernetes.io/part-of" = "openbi-platform"
    }
  }

  depends_on = [null_resource.wait_for_api]
}

resource "kubernetes_namespace" "openbi" {
  metadata {
    name = "openbi"
    labels = {
      "app.kubernetes.io/name"    = "openbi"
      "app.kubernetes.io/part-of" = "openbi-platform"
    }
  }

  depends_on = [null_resource.wait_for_api]
}
