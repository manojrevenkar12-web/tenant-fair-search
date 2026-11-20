# 0002. One shared index, routed and filtered by tenant, with the filter enforced in one place

**Context.** Index-per-tenant keeps data apart but multiplies shards and mappings with every shop; most shops are
small. A shared index scales with traffic, not with the number of tenants, but one missing filter leaks a shop's
catalogue to another.

**Decision.** One `products` index with `_routing` required. Document ids are `tenant:id`; every request carries
`routing=<tenant>`; every request body is built in `Queries`, and every builder adds `term: {tenant}`. The tenant
comes from the path and must match `service.tenantPattern` before anything else runs. `TenantScopeSuite` checks the
builders; the evaluation fails if a shop receives a product id that is not its own.

**Consequences.** A very large tenant shares a shard with others; if one grows past a threshold it can move to
its own index behind the same `Es` class. Mappings are shared, so a per-tenant attribute needs a generic field.
