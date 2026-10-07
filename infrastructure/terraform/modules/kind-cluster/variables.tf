variable "cluster_name" {
  description = "Name of the Kind cluster"
  type        = string
}

variable "node_image" {
  description = "Kind node image"
  type        = string
  default     = "kindest/node:v1.30.2"
}

variable "worker_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 1
}

variable "kubeconfig" {
  description = "Kubeconfig file path"
  type        = string
  default     = "~/.kube/config"
}
