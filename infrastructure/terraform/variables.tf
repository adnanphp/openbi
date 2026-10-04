variable "cluster_name" {
  description = "Name of the Kind cluster"
  type        = string
  default     = "openbi"
}

variable "node_image" {
  description = "Kind node image version"
  type        = string
  default     = "kindest/node:v1.27.3"
}

variable "worker_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 2
}

variable "kubeconfig_path" {
  description = "Path to the kubeconfig file"
  type        = string
  default     = "/home/adnan/.kube/config"
}
