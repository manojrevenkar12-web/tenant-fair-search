"""python -m tfs.eval.cli evaluate | heldout | smoke | gate | readme"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys

from tfs import settings
from tfs.eval import gate, report
from tfs.eval.run import evaluate
from tfs.settings import CONFIG, ROOT

LOCK = CONFIG / "heldout.lock"


def _write(name: str, rep: dict) -> None:
    report.REPORTS.mkdir(parents=True, exist_ok=True)
    (report.REPORTS / f"{name}.json").write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n")


def _config_sha() -> str:
    h = hashlib.sha256()
    for name in ("platform.json", "index.json", "world.yaml", "catalogue.yaml", "gate.yaml"):
        h.update((CONFIG / name).read_bytes())
    return h.hexdigest()[:16]


def readme(check: bool) -> int:
    dev = report.load("dev")
    if dev is None:
        print("no reports/dev.json yet")
        return 0 if not check else 1
    held = report.load("heldout")
    block = report.block(dev, held, gate.check(dev), gate.check(held) if held else None)
    text = report.README.read_text()
    new = report.render_readme(text, block)
    if check:
        if new != text:
            print("README results block is out of date: run python -m tfs.eval.cli readme")
            return 1
        return 0
    report.README.write_text(new)
    report.write_charts(dev)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("evaluate", help="the development worlds, every design, relevance and load")
    sub.add_parser("heldout", help="the held-out worlds, once")
    sm = sub.add_parser("smoke", help="one world, fewer queries: the CI end-to-end check")
    sm.add_argument("--queries", type=int, default=80)
    g = sub.add_parser("gate")
    g.add_argument("--heldout", action="store_true")
    r = sub.add_parser("readme")
    r.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "evaluate":
        rep = evaluate(settings.world()["seeds"])
        _write("dev", rep)
        readme(check=False)
        print(json.dumps(gate.check(rep), indent=2))
        return 0
    if a.cmd == "heldout":
        if LOCK.exists():
            print(f"the held-out worlds were already evaluated: {LOCK.read_text().strip()}")
            return 1
        seeds = settings.heldout()["seeds"]
        LOCK.write_text(json.dumps({"ran_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "config_sha": _config_sha(), "seeds": seeds}) + "\n")
        rep = evaluate(seeds)
        _write("heldout", rep)
        readme(check=False)
        print(json.dumps(gate.check(rep), indent=2))
        return 0
    if a.cmd == "smoke":
        rep = evaluate(settings.world()["seeds"][:1], queries=a.queries)
        d = rep["designs"]
        print(json.dumps({k: {"ndcg": v["ndcg"], "sku_first": v["sku_first"], "es_ms": v["es_ms"]} for k, v in d.items()}, indent=2))
        print(json.dumps(rep["load"]["fair"] | {"capacity_qps": rep["load"]["capacity_qps"]}, indent=2))
        problems = []
        if d["routed"]["ndcg"] <= d["lexical"]["ndcg"]:
            problems.append("routed is not better than lexical")
        if (d["routed"]["sku_first"] or 0) < 0.9:
            problems.append("SKU lookups miss")
        if rep["load"]["fair"]["quiet_burst_failed"] > 0.02:
            problems.append("quiet shops fail during a burst under fair admission")
        for p in problems:
            print("SMOKE FAILED:", p)
        return 1 if problems else 0
    if a.cmd == "gate":
        rep = report.load("heldout" if a.heldout else "dev")
        if rep is None:
            print("no report")
            return 1
        res = gate.check(rep)
        for name, ok in res["checks"].items():
            print(("PASS " if ok else "FAIL ") + name)
        return 0 if res["passed"] else 1
    if a.cmd == "readme":
        return readme(a.check)
    return 2


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["main", "ROOT"]
