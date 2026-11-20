# Repeatable tasks

## Add a design
1. Add its switches to `designs` in `config/platform.json` (and to `Design` in `Platform.scala` if it needs a new switch).
2. If it needs new behaviour, put it in `Router.plan`, with a unit test in `RouterSuite`.
3. Run the `evaluate` workflow with `set=dev`, commit `reports/` and `README.md`. It appears in every table.

## Change a relevance setting (weights, candidates, fields)
1. Edit `retrieval` in `config/platform.json`. 2. Run the dev evaluation. 3. Keep it only if the paired
interval against the previous `routed` result excludes zero. Never look at held-out numbers to decide.

## Onboard a tenant
1. Choose a name that matches `service.tenantPattern`.
2. Train its term model from its own feed and purchase logs (`tfs.learn.terms.train`) and publish
   `<tenant>.json` to the models volume.
3. `POST /v1/tenants/<tenant>/products` in batches of at most `service.maxBulk`.
4. Check `GET /v1/metrics` for its counters after first traffic.

## Change a tenant's rate or share
Edit `admission` in `config/platform.json`; `ratePerSecond`, `burst` and `tenantShare` apply to every tenant.
Re-run the dev evaluation: the isolation table shows the effect on the other shops.

## Run the held-out evaluation (once)
Only after the dev gate passes and nothing will change: run `evaluate` with `set=heldout`, download the
artifact, commit `reports/heldout.json`, `README.md` and `config/heldout.lock` together.

## Regenerate the README block
`python -m tfs.eval.cli readme` (CI runs it with `--check`).
