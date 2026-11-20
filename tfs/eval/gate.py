"""The release gate: thresholds from config/gate.yaml, checked on a report."""

from __future__ import annotations

from tfs import settings


def check(rep: dict) -> dict:
    g = settings.gate()
    d = rep["designs"]
    routed, hybrid, lexical = d["routed"], d["hybrid_rrf"], d["lexical"]
    vs_hybrid = rep["comparisons"]["routed - hybrid_rrf"]
    vs_lexical = rep["comparisons"]["routed - lexical"]
    checks = {
        "routed beats lexical by the minimum gain (lower bound of the paired interval)": vs_lexical["ci"][0] >= g["min_gain_over_lexical"],
        "routed is not worse than fusing every query (lower bound of the paired interval)": vs_hybrid["ci"][0] >= -g["max_loss_vs_hybrid"],
        "SKU lookups put the product first": (routed["sku_first"] or 0.0) >= g["min_sku_first"],
        "top-10 results rarely break a stated constraint": routed["violations_top10"] <= g["max_violations_top10"],
        "cluster cost per query is not above fusing every query": routed["cost_per_1000_eur"] <= hybrid["cost_per_1000_eur"] * g["max_cost_vs_hybrid"],
        "lexical baseline is not better than routed on any shape": all(
            routed["by_shape"][s] + g["shape_tolerance"] >= lexical["by_shape"][s] for s in routed["by_shape"]
        ),
    }
    ld = rep.get("load")
    if ld:
        f = ld["fair"]
        checks["other shops' p99 during a burst stays under the bound"] = f["quiet_burst_p99_ms"] <= g["max_quiet_burst_p99_ms"]
        checks["other shops' searches do not fail during a burst"] = f["quiet_burst_failed"] <= g["max_quiet_burst_failed"]
    return {"passed": all(checks.values()), "checks": checks}
