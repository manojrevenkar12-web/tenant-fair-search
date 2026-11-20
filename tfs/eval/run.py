"""Evaluates every design on the worlds of a seed set, against the running service and cluster."""

from __future__ import annotations

import asyncio
import os
from collections import defaultdict
from pathlib import Path

import numpy as np

from tfs import settings
from tfs.eval import load, relevance
from tfs.eval.client import Service, session
from tfs.eval.metrics import mean_ci
from tfs.learn import terms
from tfs.settings import ROOT
from tfs.world.shops import world

MODELS = Path(os.environ.get("TFS_MODEL_DIR", ROOT / settings.platform()["service"]["modelDir"]))
SHAPES = ["keyword", "sentence", "agent", "sku"]


async def prepare(service: Service, shops) -> dict:
    """Trains each tenant's term model from its own history, then re-indexes its feed."""
    out = {}
    for s in shops:
        model = terms.train(s.name, [p.feed() for p in s.products], s.logs)
        terms.write(model, MODELS)
        await service.clear(s.name)
        out[s.name] = {"indexed": await service.index(s.name, [p.feed() for p in s.products]), "terms": len(model["terms"])}
    return out


async def evaluate_seed(seed: int, designs: list[str], with_load: bool, queries: int | None, concurrency: int) -> dict:
    shops = world(seed)
    if queries is not None:
        for s in shops:
            s.queries = s.queries[:queries]
    async with session() as http:
        service = Service(http)
        if not await service.health():
            raise SystemExit(f"the service is not answering at {service.url}")
        prepared = await prepare(service, shops)
        rows = []
        k = settings.platform()["retrieval"]["k"]
        for d in designs:
            for s in shops:
                rows.extend(await relevance.score_design(service, s, d, seed, k, concurrency))
        loaded = await load.run(service, shops, seed) if with_load else None
    return {"seed": seed, "prepared": prepared, "rows": rows, "load": loaded}


def evaluate(seeds: list[int], with_load: bool = True, queries: int | None = None, concurrency: int = 8) -> dict:
    designs = list(settings.platform()["designs"])
    per_seed = [asyncio.run(evaluate_seed(s, designs, with_load, queries, concurrency)) for s in seeds]
    return summarise(per_seed, designs, seeds)


def summarise(per_seed: list[dict], designs: list[str], seeds: list[int]) -> dict:
    rows = [r for s in per_seed for r in s["rows"]]
    key = seeds[0]
    by = defaultdict(list)
    for r in rows:
        by[r["design"]].append(r)

    def block(rs: list[dict], name: str) -> dict:
        nd = mean_ci([r["ndcg"] for r in rs], key, name)
        sku = [r for r in rs if r["shape"] == "sku"]
        nonsku = [r for r in rs if r["shape"] != "sku"]
        returned = sum(r["returned"] for r in nonsku)
        return {
            "queries": len(rs),
            "ndcg": nd[0],
            "ndcg_ci": [nd[1], nd[2]],
            "by_shape": {sh: float(np.mean([r["ndcg"] for r in rs if r["shape"] == sh])) for sh in SHAPES if any(r["shape"] == sh for r in rs)},
            "sku_first": float(np.mean([r["first_ok"] for r in sku])) if sku else None,
            "first_ok": float(np.mean([r["first_ok"] for r in nonsku])) if nonsku else None,
            "violations_top10": (sum(r["violations"] for r in nonsku) / returned) if returned else 0.0,
            "zero_results": float(np.mean([r["zero"] for r in rs])),
            "es_ms": float(np.mean([r["es_ms"] for r in rs])),
            "cost_per_1000_eur": float(np.mean([r["cost_eur"] for r in rs]) * 1000.0),
            "plans": {p: sum(1 for r in rs if r["plan"] == p) for p in sorted({r["plan"] for r in rs})},
        }

    out_designs = {d: block(by[d], d) for d in designs}

    def paired(a: str, b: str) -> dict:
        ia = {(r["seed"], r["query"]): r["ndcg"] for r in by[a]}
        diffs = [ia[(r["seed"], r["query"])] - r["ndcg"] for r in by[b] if (r["seed"], r["query"]) in ia]
        m = mean_ci(diffs, key, f"{a}-{b}")
        return {"mean": m[0], "ci": [m[1], m[2]], "n": len(diffs)}

    comparisons = {
        f"routed - {b}": paired("routed", b) for b in designs if b != "routed"
    }

    loads = [s["load"] for s in per_seed if s["load"]]
    load_summary = None
    if loads:
        load_summary = {"capacity_qps": float(np.mean([x["capacity_qps"] for x in loads])), "seeds": len(loads)}
        for mode in ("none", "fair"):
            keys = loads[0][mode].keys()
            load_summary[mode] = {k: float(np.nanmean([x[mode][k] for x in loads])) for k in keys}
        load_summary["per_seed"] = loads

    world_cfg = settings.world()
    return {
        "seeds": seeds,
        "tenants": [t["name"] for t in world_cfg["tenants"]],
        "products": sum(t["products"] for t in world_cfg["tenants"]),
        "queries_per_seed": len(rows) // max(1, len(designs)) // max(1, len(seeds)),
        "shapes": {sh: sum(1 for r in by[designs[0]] if r["shape"] == sh) for sh in SHAPES},
        "prepared": [s["prepared"] for s in per_seed],
        "designs": out_designs,
        "comparisons": comparisons,
        "load": load_summary,
    }
