# Loki — log aggregation. Promtail — log shipper (DaemonSet).
#
# Loki runs in single-binary mode (one pod) with filesystem storage.

resource "kubernetes_namespace" "logging" {
  metadata {
    name = "logging"
    labels = {
      "app.kubernetes.io/name"    = "logging"
      "app.kubernetes.io/part-of" = "openbi-platform"
    }
  }

  depends_on = [null_resource.wait_for_api]
}

resource "helm_release" "loki" {
  name      = "loki"
  namespace = kubernetes_namespace.logging.metadata[0].name

  repository = "https://grafana.github.io/helm-charts"
  chart      = "loki"
  version    = "~> 5.0"

  # Minimal single-binary config. Let the chart defaults handle most
  # things; we only override deployment mode and schema.
  values = [yamlencode({
    deploymentMode = "SingleBinary"

    loki = {
      auth_enabled = false

      commonConfig = {
        replication_factor = 1
      }

      storage = {
        type = "filesystem"
      }

      # Loki 2.8 (chart 5.x) supports schema versions v11 and v12.
      # v13 requires Loki 3.x.
      schemaConfig = {
        configs = [
          {
            from         = "2024-01-01"
            store        = "boltdb-shipper"
            object_store = "filesystem"
            schema       = "v12"
            index = {
              prefix = "loki_index_"
              period = "24h"
            }
          }
        ]
      }
    }

    singleBinary = {
      replicas = 1
      persistence = {
        enabled      = true
        size         = "2Gi"
        storageClass = "standard"
      }
    }

    # Disable the distributed components that are unused in SingleBinary.
    read    = { replicas = 0 }
    write   = { replicas = 0 }
    backend = { replicas = 0 }

    chunksCache  = { enabled = false }
    resultsCache = { enabled = false }
    lokiCanary   = { enabled = false }
    test         = { enabled = false }

    monitoring = {
      selfMonitoring = { enabled = false }
      lokiCanary     = { enabled = false }
      serviceMonitor = { enabled = false }
    }
  })]

  # Give Helm more time to become ready
  timeout = 600

  depends_on = [kubernetes_namespace.logging]
}

resource "helm_release" "promtail" {
  name      = "promtail"
  namespace = kubernetes_namespace.logging.metadata[0].name

  repository = "https://grafana.github.io/helm-charts"
  chart      = "promtail"
  version    = "~> 6.0"

  values = [yamlencode({
    config = {
      clients = [{
        url = "http://loki-gateway.logging.svc.cluster.local/loki/api/v1/push"
      }]
    }
  })]

  timeout = 600

  depends_on = [helm_release.loki]
}

# Expose Loki's API externally via NodePort so the Compose Grafana
# (running outside the Kind cluster) can reach it.
resource "kubernetes_service" "loki_external" {
  metadata {
    name      = "loki-external"
    namespace = kubernetes_namespace.logging.metadata[0].name
  }

  spec {
    type = "NodePort"
    selector = {
      "app.kubernetes.io/name"      = "loki"
      "app.kubernetes.io/component" = "single-binary"
    }

    port {
      name        = "http"
      port        = 3100
      target_port = 3100
      node_port   = 30310
    }
  }

  depends_on = [helm_release.loki]
}
