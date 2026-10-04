output "cluster_name" {
  description = "Name of the created Kind cluster"
  value       = module.kind_cluster.cluster_name
}

output "kubeconfig_path" {
  description = "Path to the kubeconfig file for the cluster"
  value       = module.kind_cluster.kubeconfig_path
}

output "cluster_endpoint" {
  description = "Kubernetes API server endpoint"
  value       = module.kind_cluster.cluster_endpoint
  sensitive   = true
}

output "kubectl_context" {
  description = "kubectl context name for the cluster"
  value       = "kind-${module.kind_cluster.cluster_name}"
}
