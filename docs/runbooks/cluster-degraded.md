# Runbook: the cluster is slow or red

**Signal.** 503 "search timed out" rises for every tenant at once; Elasticsearch health is yellow or red.

1. `GET _cluster/health` and `GET _cat/nodes?v` through the ECK service: a lost node, disk watermark, or heap.
2. While degraded, lower `admission.globalConcurrency` so requests fail fast with 429/503 instead of piling up
   inside the cluster; roll out the config map.
3. If one tenant's re-index is running, pause it: bulk indexing competes with search on the same nodes.
4. When healthy, restore the setting and check that p99 is back to its calm level for every tenant.
