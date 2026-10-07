# Wait for the Kind cluster's API server to be fully ready before
# applying manifests.
#
# The kind provider returns as soon as the cluster container starts, but
# kube-apiserver, kubelet, and the internal networking take an additional
# 15-40 seconds to become fully responsive. Without this delay,
# kubectl_manifest resources race the API server and get spurious 404s.

resource "null_resource" "wait_for_api" {
  depends_on = [module.kind_cluster]

  triggers = {
    cluster_name = module.kind_cluster.cluster_name
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      echo "Waiting for cluster API to be ready..."
      for i in $(seq 1 60); do
        if kubectl --context kind-${module.kind_cluster.cluster_name} get --raw='/readyz' >/dev/null 2>&1; then
          echo "Cluster API is ready"
          sleep 15
          exit 0
        fi
        sleep 1
      done
      echo "Cluster API did not become ready in 60 seconds"
      exit 1
    EOT
  }
}
