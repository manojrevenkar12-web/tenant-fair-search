# Working on tenant-fair-search

A multi-tenant product search service (Scala 3, cats-effect, http4s) in front of one Elasticsearch cluster, and
the simulated shops (Python) that measure it. Read this before changing anything.

## Fast feedback

| What | Command | Where it runs |
|---|---|---|
| Service unit tests | `sbt "service/test"` | CI `scala` (needs Maven Central) |
| World, term model, metrics, gate | `python -m pytest -q` and `ruff check .` | anywhere |
| End to end on one world | start Elasticsearch and the jar with `TFS_EVAL_OVERRIDES=true`, then `python -m tfs.eval.cli smoke` | CI `e2e` |
| Dashboard | `cd web && pnpm build && pnpm e2e` | CI `web` |
| Chart and Terraform | `helm lint`, `helm template … \| kubeconform -strict`, `terraform validate` | CI `infra` |
| Full development evaluation | `evaluate` workflow, `set=dev`; commit the artifact's `reports/` and `README.md` | Actions |

## Invariants

1. **The truth stays in the world.** Category and features are hidden attributes of `tfs.world.shops.Product`.
   The feed (`Product.feed()`), the queries and the purchase logs are all the platform sees. Only the evaluation
   grades answers against the truth.
2. **The world does not read the product's settings.** `tfs/world/*` reads `config/world.yaml` and
   `config/catalogue.yaml`, never `config/platform.json`. Shoppers' colour words and the platform's colour
   synonyms are configured separately, on purpose.
3. **Same luck for every design.** Every random draw comes from `tfs.world.luck.stream(seed, *keys)`. All designs
   answer the same queries; both admission modes get the same arrival schedule.
4. **The model reads and code decides.** The term model only proposes a vector. Which plan runs, which filters
   apply and who is admitted are rules in `tfs.retrieve.Router`, `tfs.understand.Parser` and `tfs.tenancy.Gate`.
5. **Every query is scoped to its tenant.** Request bodies are built only in `tfs.retrieve.Queries`, every builder
   adds the tenant filter, requests are routed by tenant, and `TenantScopeSuite` fails if a builder forgets.
   The evaluation also fails if a shop ever receives another shop's product id.
6. **One tokenizer rule.** The pattern, stopwords and minimum length live in `config/platform.json`; Scala and
   Python both check `tests/fixtures/tokenize.json`.
7. **Settings in config.** Thresholds, weights, rates and prices are in `config/*.json|yaml`; Terraform mounts
   the same files into the cluster. No copies.
8. **Generated reports.** `reports/*.json`, `reports/charts/*.svg` and the README block between the results
   markers come from `tfs.eval`; CI fails if the README block and the reports disagree.

## The held-out rule

`config/heldout.yaml` lists seeds that are evaluated once, by the `evaluate` workflow with `set=heldout`, after
every setting is fixed on the development seeds. The run writes `config/heldout.lock`; `python -m tfs.eval.cli
heldout` refuses to run again while the lock exists. Never tune anything on held-out numbers.
