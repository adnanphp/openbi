# Provider configuration for the application layer (Phase 6).
#
# The kubectl provider source is declared in main.tf alongside the kind,
# kubernetes, and helm providers. This file only configures it — it does
# not redeclare required_providers.

provider "kubectl" {
  config_path      = module.kind_cluster.kubeconfig_path
  config_context   = "kind-${var.cluster_name}"
  load_config_file = false
}
