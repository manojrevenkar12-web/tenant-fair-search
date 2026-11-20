locals {
  config_dir = "${path.module}/../../config"
  chart_dir  = "${path.module}/../helm/tenant-fair-search"
}

resource "kubernetes_namespace" "search" {
  metadata {
    name = var.namespace
  }
}

# The service's settings, straight from the repository's config files: one source for every environment.
resource "kubernetes_config_map" "config" {
  metadata {
    name      = "tenant-fair-search-config"
    namespace = kubernetes_namespace.search.metadata[0].name
  }
  data = {
    "platform.json" = file("${local.config_dir}/platform.json")
    "index.json"    = file("${local.config_dir}/index.json")
  }
}

resource "kubernetes_persistent_volume_claim" "models" {
  metadata {
    name      = "tenant-fair-search-models"
    namespace = kubernetes_namespace.search.metadata[0].name
  }
  spec {
    access_modes = ["ReadOnlyMany"]
    resources {
      requests = { storage = var.models_storage }
    }
  }
  wait_until_bound = false
}

# Elastic Cloud on Kubernetes runs the cluster.
resource "helm_release" "eck_operator" {
  name             = "eck-operator"
  repository       = "https://helm.elastic.co"
  chart            = "eck-operator"
  version          = "2.14.0"
  namespace        = "elastic-system"
  create_namespace = true
}

resource "kubernetes_manifest" "elasticsearch" {
  depends_on = [helm_release.eck_operator]
  manifest = {
    apiVersion = "elasticsearch.k8s.elastic.co/v1"
    kind       = "Elasticsearch"
    metadata   = { name = "search", namespace = kubernetes_namespace.search.metadata[0].name }
    spec = {
      version = var.es_version
      http    = { tls = { selfSignedCertificate = { disabled = true } } }
      nodeSets = [{
        name  = "data"
        count = var.es_nodes
        config = {
          "node.store.allow_mmap" = false
        }
        podTemplate = {
          spec = {
            containers = [{
              name      = "elasticsearch"
              resources = { requests = { cpu = "2", memory = "8Gi" }, limits = { memory = "8Gi" } }
            }]
          }
        }
        volumeClaimTemplates = [{
          metadata = { name = "elasticsearch-data" }
          spec = {
            accessModes = ["ReadWriteOnce"]
            resources   = { requests = { storage = var.es_storage } }
          }
        }]
      }]
    }
  }
}

resource "helm_release" "service" {
  depends_on = [kubernetes_config_map.config, kubernetes_manifest.elasticsearch]
  name       = "tenant-fair-search"
  chart      = local.chart_dir
  namespace  = kubernetes_namespace.search.metadata[0].name

  set {
    name  = "image.tag"
    value = var.image_tag
  }
  set {
    name  = "configMap"
    value = kubernetes_config_map.config.metadata[0].name
  }
  set {
    name  = "elasticsearch.url"
    value = "http://search-es-http.${var.namespace}.svc:9200"
  }
  set {
    name  = "models.claimName"
    value = kubernetes_persistent_volume_claim.models.metadata[0].name
  }
}
