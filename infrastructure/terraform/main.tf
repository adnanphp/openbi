terraform {
  required_version = ">= 1.5.0"

  required_providers {
    kind = {
      source  = "tehcyx/kind"
      version = "~> 0.5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
    kubectl = {
      source  = "gavinbunney/kubectl"
      version = "~> 1.14"
    }
  }
}

module "kind_cluster" {
  source = "./modules/kind-cluster"

  cluster_name = var.cluster_name
  node_image   = var.node_image
  worker_count = var.worker_count
  kubeconfig   = var.kubeconfig_path
}

provider "kubernetes" {
  config_path    = module.kind_cluster.kubeconfig_path
  config_context = "kind-${var.cluster_name}"
}

provider "helm" {
  kubernetes {
    config_path    = module.kind_cluster.kubeconfig_path
    config_context = "kind-${var.cluster_name}"
  }
}
