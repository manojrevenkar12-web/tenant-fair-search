"""Every design answers every query of a world; the answers are scored against the hidden grades."""

from __future__ import annotations

import asyncio

from tfs.eval.client import Service
from tfs.eval.metrics import ndcg
from tfs.world.shops import Query, Shop, violates


async def score_design(service: Service, shop: Shop, design: str, seed: int, k: int, concurrency: int) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)

    async def one(q: Query) -> dict:
        async with sem:
            ans = await service.search(shop.name, q.body(), design=design, admission="none")
        if ans.status != 200 or ans.body is None:
            raise RuntimeError(f"{design} {shop.name} {q.id}: HTTP {ans.status}")
        ranked = [h["id"] for h in ans.body["hits"]][:k]
        grades = shop.grades(q)
        top = ranked[:k]
        foreign = [pid for pid in top if pid not in shop.by_id]
        if foreign:
            raise RuntimeError(f"{shop.name} received another tenant's products: {foreign[:3]}")
        violations = sum(1 for pid in top if violates(shop.by_id[pid], q.intent)) if top else 0
        return {
            "seed": seed,
            "tenant": shop.name,
            "query": q.id,
            "shape": q.shape,
            "design": design,
            "plan": ans.body["plan"],
            "ndcg": ndcg(ranked, grades, k),
            "first_ok": bool(ranked) and grades.get(ranked[0], 0) >= (3 if q.intent.target else 2),
            "violations": violations,
            "returned": len(top),
            "zero": not ranked,
            "es_ms": ans.body["esTookMs"],
            "cost_eur": ans.body["costEur"],
            "client_ms": ans.ms,
        }

    return list(await asyncio.gather(*(one(q) for q in shop.queries)))
