variable "kubeconfig" {
  type    = string
  default = "~/.kube/config"
}

variable "kube_context" {
  type    = string
  default = null
}

variable "namespace" {
  type    = string
  default = "search"
}

variable "image_tag" {
  type    = string
  default = "0.1.0"
}

variable "es_version" {
  type    = string
  default = "8.15.3"
}

variable "es_nodes" {
  description = "Data nodes. Tenants share one index routed by tenant, so nodes scale with traffic, not with tenant count."
  type        = number
  default     = 3
}

variable "es_storage" {
  type    = string
  default = "100Gi"
}

variable "models_storage" {
  type    = string
  default = "5Gi"
}
