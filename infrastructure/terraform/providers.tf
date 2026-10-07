# Provider configuration for the application layer (Phase 6).
#
# The kubectl provider source is declared in main.tf alongside the kind,
# kubernetes, and helm providers.
#
# Note: `load_config_file = true` is required — the provider needs to
# read the kubeconfig and resolve the context. Setting it to false makes
# the provider fall back to $KUBECONFIG or localhost defaults, which
# fails on Kind.

provider "kubectl" {
  config_path      = module.kind_cluster.kubeconfig_path
  config_context   = "kind-${var.cluster_name}"
  load_config_file = true
}
