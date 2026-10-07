variable "cluster_name" {
  description = "Name of the Kind cluster"
  type        = string
  default     = "openbi"
}

variable "node_image" {
  description = "Kind node image version"
  type        = string
  default     = "kindest/node:v1.30.2"
}

variable "worker_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 1
}

variable "kubeconfig_path" {
  description = "Absolute path to the kubeconfig file (tilde is not expanded by the kind provider)"
  type        = string
  default     = "/home/adnan/.kube/config"
}
