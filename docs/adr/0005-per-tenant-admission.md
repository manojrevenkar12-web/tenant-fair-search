# 0005. Per-tenant admission in front of the cluster

**Context.** AI shopping agents query far faster than people and in bursts. With one shared queue in front of the
cluster, one shop's agent fills it and every other shop's shoppers wait behind it.

**Decision.** `Gate` admits each request through the tenant's token bucket (`ratePerSecond`, `burst`), then a
per-tenant semaphore that holds at most `tenantShare` of the cluster's search slots, then the global semaphore of
`globalConcurrency` slots. Over-rate requests get 429 with Retry-After at once instead of queueing; requests that
wait past `requestTimeoutMs` get 503. The evaluation plays the same burst against "fair" and "none".

**Consequences.** A shop's agent is throttled to its plan even when the cluster has spare capacity at that moment;
plans with a higher rate are a config change. The limits are per service replica; with N replicas behind a load
balancer the effective rate is N times higher unless the bucket moves to a shared store.
