# Runbook: one tenant is slowing everyone down

**Signal.** p99 for several tenants rises together; `GET /v1/metrics` shows one tenant with a fast-growing
`limited` count, or (with admission off) a fast-growing `admitted` count.

1. Confirm admission is on: `admission.mode` is `fair` in the mounted `platform.json`. If an override header is
   being honoured in production, `service.evalOverrides` is wrong: set it to `false` and roll out.
2. Find the tenant: the counters by tenant in `/v1/metrics`, and the gateway's request logs.
3. If the traffic is legitimate (an agent integration): agree a plan with the shop and raise its rate. Today the rate
   is global; a per-tenant plan table is the follow-up.
4. If the 429s are not making the agent back off, block it at the gateway and contact the shop.
5. Afterwards: check that the other tenants' p99 went back to their calm level, and write down the peak rate.
