"""Metrics, the gate and the generated README block, on a report shaped like the real one."""

import copy

from tfs.eval import gate, report
from tfs.eval.metrics import mean_ci, ndcg


def test_ndcg():
    grades = {"a": 3, "b": 2, "c": 1}
    assert ndcg(["a", "b", "c"], grades) == 1.0
    assert ndcg(["c", "b", "a"], grades) < 1.0
    assert ndcg([], grades) == 0.0
    assert ndcg(["z"], {}) == 0.0


def test_interval_contains_the_mean_and_is_repeatable():
    m, lo, hi = mean_ci([0.1, 0.5, 0.9, 0.4], 1, "k")
    assert lo <= m <= hi
    assert mean_ci([0.1, 0.5, 0.9, 0.4], 1, "k") == (m, lo, hi)


def _design(ndcg_, cost=0.01, sku=1.0, viol=0.01):
    shapes = {"keyword": ndcg_, "sentence": ndcg_, "agent": ndcg_, "sku": sku}
    return {"queries": 10, "ndcg": ndcg_, "ndcg_ci": [ndcg_ - 0.01, ndcg_ + 0.01], "by_shape": shapes, "sku_first": sku,
            "first_ok": 0.5, "violations_top10": viol, "zero_results": 0.0, "es_ms": 5.0, "cost_per_1000_eur": cost, "plans": {}}


def fake_report():
    designs = {name: _design(v) for name, v in {"lexical": 0.4, "semantic": 0.5, "hybrid_rrf": 0.6, "hybrid_with_understanding": 0.65,
                                               "routed_without_understanding": 0.6, "routed": 0.66}.items()}
    designs["routed"]["cost_per_1000_eur"] = 0.009
    comps = {f"routed - {d}": {"mean": 0.66 - v["ndcg"], "ci": [0.66 - v["ndcg"] - 0.005, 0.66 - v["ndcg"] + 0.005], "n": 100}
             for d, v in designs.items() if d != "routed"}
    side = {"quiet_calm_p50_ms": 5, "quiet_calm_p99_ms": 20, "quiet_burst_p50_ms": 6, "quiet_burst_p99_ms": 40, "quiet_burst_failed": 0.0,
            "quiet_requests_in_burst": 100, "noisy_sent_in_burst": 1000, "noisy_limited_share": 0.7, "noisy_failed_share": 0.0,
            "noisy_served_in_burst": 300}
    load = {"capacity_qps": 500.0, "seeds": 1, "fair": dict(side), "none": dict(side, quiet_burst_p99_ms=2000, quiet_burst_failed=0.3)}
    return {"seeds": [1], "tenants": ["a", "b"], "products": 10, "queries_per_seed": 10,
            "shapes": {"keyword": 4, "sentence": 3, "agent": 2, "sku": 1}, "designs": designs, "comparisons": comps, "load": load}


def test_gate_passes_a_good_report_and_fails_a_slow_one():
    rep = fake_report()
    assert gate.check(rep)["passed"], gate.check(rep)
    slow = copy.deepcopy(rep)
    slow["load"]["fair"]["quiet_burst_p99_ms"] = 5000
    assert not gate.check(slow)["passed"]
    costly = copy.deepcopy(rep)
    costly["designs"]["routed"]["cost_per_1000_eur"] = 1.0
    assert not gate.check(costly)["passed"]


def test_readme_block_and_charts_render():
    rep = fake_report()
    text = report.block(rep, rep, gate.check(rep), gate.check(rep))
    assert text.startswith(report.START) and text.endswith(report.END)
    assert "Held-out worlds (run once)" in text
    assert "<svg" in report.chart_shapes(rep) and "<svg" in report.chart_isolation(rep)
