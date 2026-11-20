"""One shop's AI shopping agent bursts while the other shops keep searching.

The cluster's capacity is measured first, then the same arrival schedule (same luck) is played against the service
twice: once with one shared queue ("none") and once with per-tenant admission ("fair"). What matters is what the
quiet shops' shoppers see during the burst.
"""

from __future__ import annotations

import asyncio
import time

import numpy as np

from tfs import settings
from tfs.eval.client import Service
from tfs.eval.metrics import percentile
from tfs.world.luck import stream
from tfs.world.shops import Shop


async def capacity(service: Service, shops: list[Shop], seed: int) -> float:
    """Searches a second the service sustains with many clients and no admission limits."""
    cfg = settings.world()["load"]
    rng = stream(seed, "load", "calibrate")
    pool = [(s.name, q.body()) for s in shops for q in s.queries]
    stop = time.perf_counter() + cfg["calibrate_seconds"]
    done = 0

    async def worker(w: int) -> None:
        nonlocal done
        local = stream(seed, "load", "worker", w)
        while time.perf_counter() < stop:
            tenant, body = pool[int(local.integers(len(pool)))]
            ans = await service.search(tenant, body, admission="none")
            if ans.status == 200:
                done += 1

    rng.random()
    start = time.perf_counter()
    await asyncio.gather(*(worker(w) for w in range(cfg["calibrate_concurrency"])))
    return done / (time.perf_counter() - start)


def schedule(shops: list[Shop], seed: int, cap: float) -> list[tuple[float, str, str, dict]]:
    """(time, tenant, phase, body), the same for every admission mode."""
    cfg = settings.world()["load"]
    warm, burst, cool = cfg["warm_seconds"], cfg["burst_seconds"], cfg["cool_seconds"]
    total = warm + burst + cool
    quiet_rate = cfg["quiet_share_of_capacity"] * cap / len(shops)
    noisy_rate = cfg["noisy_times_capacity"] * cap
    events = []
    for s in shops:
        rng = stream(seed, "load", "arrivals", s.name)
        bodies = [q.body() for q in s.queries]
        t = 0.0
        while True:
            in_burst = s.name == cfg["noisy_tenant"] and warm <= t < warm + burst
            t += float(rng.exponential(1.0 / (noisy_rate if in_burst else quiet_rate)))
            if t >= total:
                break
            phase = "calm" if t < warm else ("burst" if t < warm + burst else "after")
            events.append((t, s.name, phase, bodies[int(rng.integers(len(bodies)))]))
    events.sort(key=lambda e: e[0])
    return events


async def play(service: Service, events: list[tuple[float, str, str, dict]], mode: str) -> list[dict]:
    cfg = settings.world()["load"]
    results: list[dict] = []
    start = time.perf_counter()

    async def fire(tenant: str, phase: str, body: dict) -> None:
        ans = await service.search(tenant, body, admission=mode, timeout=cfg["client_timeout_seconds"])
        results.append({"tenant": tenant, "phase": phase, "status": ans.status, "ms": ans.ms})

    tasks = []
    for t, tenant, phase, body in events:
        delay = t - (time.perf_counter() - start)
        if delay > 0:
            await asyncio.sleep(delay)
        tasks.append(asyncio.create_task(fire(tenant, phase, body)))
    await asyncio.gather(*tasks)
    await asyncio.sleep(1.0)
    return results


def summarise(results: list[dict], noisy: str) -> dict:
    quiet = [r for r in results if r["tenant"] != noisy]
    loud = [r for r in results if r["tenant"] == noisy and r["phase"] == "burst"]

    def ok_ms(rows):
        return [r["ms"] for r in rows if r["status"] == 200]

    calm = [r for r in quiet if r["phase"] == "calm"]
    burst = [r for r in quiet if r["phase"] == "burst"]
    return {
        "quiet_calm_p50_ms": percentile(ok_ms(calm), 50),
        "quiet_calm_p99_ms": percentile(ok_ms(calm), 99),
        "quiet_burst_p50_ms": percentile(ok_ms(burst), 50),
        "quiet_burst_p99_ms": percentile(ok_ms(burst), 99),
        "quiet_burst_failed": float(np.mean([r["status"] != 200 for r in burst])) if burst else 0.0,
        "quiet_requests_in_burst": len(burst),
        "noisy_sent_in_burst": len(loud),
        "noisy_limited_share": float(np.mean([r["status"] == 429 for r in loud])) if loud else 0.0,
        "noisy_failed_share": float(np.mean([r["status"] not in (200, 429) for r in loud])) if loud else 0.0,
        "noisy_served_in_burst": sum(1 for r in loud if r["status"] == 200),
    }


async def run(service: Service, shops: list[Shop], seed: int) -> dict:
    cap = await capacity(service, shops, seed)
    events = schedule(shops, seed, cap)
    noisy = settings.world()["load"]["noisy_tenant"]
    out = {"capacity_qps": cap, "events": len(events)}
    for mode in ("none", "fair"):
        await asyncio.sleep(2.0)
        out[mode] = summarise(await play(service, events, mode), noisy)
    return out
