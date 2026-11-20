"""Writes the README's results block and the charts from the committed reports. Nothing here is typed by hand."""

from __future__ import annotations

import json
import math
from pathlib import Path

from tfs.settings import ROOT

REPORTS = ROOT / "reports"
CHARTS = REPORTS / "charts"
README = ROOT / "README.md"
START, END = "<!-- results:start -->", "<!-- results:end -->"

# Categorical slots 1-4 of the validated palette, in fixed order (blue, orange, aqua, yellow).
SERIES = {"routed": "#2a78d6", "lexical": "#eb6834", "semantic": "#1baf7a", "hybrid_rrf": "#eda100"}
MODES = {"fair": "#2a78d6", "none": "#eb6834"}
INK, MUTED, GRID, SURFACE = "#1d2421", "#59615d", "#e3e6e4", "#fcfcfb"

LABELS = {
    "lexical": "Lexical (BM25) only",
    "semantic": "Vector only",
    "hybrid_rrf": "Hybrid, fused, every query",
    "hybrid_with_understanding": "Hybrid + query understanding",
    "routed_without_understanding": "Routed, no query understanding",
    "routed": "Routed + query understanding",
}
SHAPE_LABELS = {"keyword": "Keywords", "sentence": "Full sentences", "agent": "AI agents", "sku": "SKU lookups"}
SHAPE_IN_TEXT = {"keyword": "keywords", "sentence": "full sentences", "agent": "AI agents", "sku": "SKU lookups"}


def load(name: str) -> dict | None:
    p = REPORTS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _svg(w: int, h: int, title: str, sub: str, body: list[str]) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="Inter, Segoe UI, sans-serif">',
            f'<rect width="{w}" height="{h}" fill="{SURFACE}"/>',
            f'<text x="20" y="28" font-size="15" font-weight="600" fill="{INK}">{title}</text>',
            f'<text x="20" y="47" font-size="12" fill="{MUTED}">{sub}</text>',
            *body,
            "</svg>",
        ]
    ) + "\n"


def chart_shapes(rep: dict) -> str:
    designs = [d for d in SERIES if d in rep["designs"]]
    shapes = [s for s in SHAPE_LABELS if s in rep["designs"]["routed"]["by_shape"]]
    w, left, right, top = 760, 130, 70, 110
    bar, gap, group_gap = 12, 2, 18
    group_h = len(designs) * (bar + gap) + group_gap
    h = top + len(shapes) * group_h + 20
    x0, x1 = left, w - right

    def X(v: float) -> float:
        return x0 + v * (x1 - x0)

    body = []
    for j, d in enumerate(designs):
        lx, ly = left + (j % 2) * 280, 60 + (j // 2) * 20
        body.append(f'<rect x="{lx}" y="{ly}" width="12" height="12" rx="2" fill="{SERIES[d]}"/>')
        body.append(f'<text x="{lx + 17}" y="{ly + 10}" font-size="12" fill="{INK}">{LABELS[d]}</text>')
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        body.append(f'<line x1="{X(t):.1f}" y1="{top - 6}" x2="{X(t):.1f}" y2="{h - 16}" stroke="{GRID}"/>')
        body.append(f'<text x="{X(t):.1f}" y="{h - 4}" font-size="11" text-anchor="middle" fill="{MUTED}">{t:.2f}</text>')
    for i, s in enumerate(shapes):
        y = top + i * group_h
        body.append(f'<text x="{left - 10}" y="{y + len(designs) * (bar + gap) / 2 + 4:.1f}" font-size="12" text-anchor="end" fill="{INK}">{SHAPE_LABELS[s]}</text>')
        for j, d in enumerate(designs):
            v = rep["designs"][d]["by_shape"].get(s, 0.0)
            yy = y + j * (bar + gap)
            body.append(f'<rect x="{x0}" y="{yy}" width="{max(X(v) - x0, 1):.1f}" height="{bar}" rx="3" fill="{SERIES[d]}"><title>{LABELS[d]}, {SHAPE_LABELS[s]}: {v:.3f}</title></rect>')
            if d == "routed":
                body.append(f'<text x="{X(v) + 6:.1f}" y="{yy + 10}" font-size="11" font-weight="600" fill="{INK}">{v:.2f}</text>')
    return _svg(w, h, "nDCG@10 by query shape", "Graded against the hidden truth; 1.0 is the best possible order", body)


def chart_isolation(rep: dict) -> str:
    load_ = rep["load"]
    w, h, left, top, bottom = 760, 300, 90, 92, 50
    phases = [("quiet_calm_p99_ms", "Before the burst"), ("quiet_burst_p99_ms", "During the burst")]
    vmax = max(load_[m][k] for m in MODES for k, _ in phases)
    lo, hi = 1.0, 10 ** math.ceil(math.log10(max(vmax, 10)))

    def Y(v: float) -> float:
        v = max(v, lo)
        return top + (h - top - bottom) * (1 - math.log10(v) / math.log10(hi))

    body = []
    lx = left
    for m, label in (("fair", "Per-tenant admission"), ("none", "One shared queue")):
        body.append(f'<rect x="{lx}" y="62" width="12" height="12" rx="2" fill="{MODES[m]}"/>')
        body.append(f'<text x="{lx + 17}" y="72" font-size="12" fill="{INK}">{label}</text>')
        lx += 200
    tick = 1.0
    while tick <= hi:
        body.append(f'<line x1="{left}" y1="{Y(tick):.1f}" x2="{w - 30}" y2="{Y(tick):.1f}" stroke="{GRID}"/>')
        body.append(f'<text x="{left - 8}" y="{Y(tick) + 4:.1f}" font-size="11" text-anchor="end" fill="{MUTED}">{tick:g} ms</text>')
        tick *= 10
    slot = (w - 30 - left) / len(phases)
    for i, (key, label) in enumerate(phases):
        cx = left + slot * i + slot / 2
        body.append(f'<text x="{cx:.1f}" y="{h - 18}" font-size="12" text-anchor="middle" fill="{INK}">{label}</text>')
        for j, m in enumerate(("fair", "none")):
            v = load_[m][key]
            x = cx - 46 + j * 50
            y = Y(v)
            body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="42" height="{h - bottom - y:.1f}" rx="3" fill="{MODES[m]}"><title>{m}: {v:.0f} ms</title></rect>')
            body.append(f'<text x="{x + 21:.1f}" y="{y - 6:.1f}" font-size="11" font-weight="600" text-anchor="middle" fill="{INK}">{v:,.0f}</text>')
    return _svg(w, h, "The other shops' slowest searches (p99) while one shop's agent bursts", "Log scale; the same arrivals played against both admission modes", body)


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v * 100:.1f}%"


def _headline(rep: dict, title: str) -> list[str]:
    d = rep["designs"]
    cols = ["routed", "hybrid_rrf", "lexical"]
    lines = [f"| {title} | " + " | ".join(LABELS[c] for c in cols) + " |", "|---|" + "---:|" * len(cols)]

    def row(name: str, f, bold: bool = True) -> None:
        cells = [f(d[c]) for c in cols]
        if bold:
            cells[0] = f"**{cells[0]}**"
        lines.append(f"| {name} | " + " | ".join(cells) + " |")

    row("nDCG@10, all queries (95% interval)", lambda x: f"{x['ndcg']:.3f} ({x['ndcg_ci'][0]:.3f} to {x['ndcg_ci'][1]:.3f})")
    for s in SHAPE_LABELS:
        if s in d["routed"]["by_shape"]:
            row(f"nDCG@10, {SHAPE_IN_TEXT[s]}", lambda x, s=s: f"{x['by_shape'][s]:.3f}")
    row("SKU lookups with the right product first", lambda x: _pct(x["sku_first"]))
    row("Top-10 results that break a stated constraint", lambda x: _pct(x["violations_top10"]))
    row("Queries with no results", lambda x: _pct(x["zero_results"]))
    row("Cluster time per query", lambda x: f"{x['es_ms']:.1f} ms")
    row("Cluster cost per 1,000 queries", lambda x: f"€{x['cost_per_1000_eur']:.4f}")
    return lines


def _designs(rep: dict) -> list[str]:
    lines = [
        "| Design | nDCG@10 | Keywords | Sentences | Agents | SKU first | Constraint breaks | Cluster ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, x in rep["designs"].items():
        b = x["by_shape"]
        label = f"**{LABELS.get(name, name)}**" if name == "routed" else LABELS.get(name, name)
        lines.append(
            f"| {label} | {x['ndcg']:.3f} | {b.get('keyword', 0):.3f} | {b.get('sentence', 0):.3f} | {b.get('agent', 0):.3f} | {_pct(x['sku_first'])} | {_pct(x['violations_top10'])} | {x['es_ms']:.1f} |"
        )
    lines += ["", "| Routed + understanding minus | Mean nDCG@10 difference (95% interval) | Paired queries |", "|---|---:|---:|"]
    for name, c in rep["comparisons"].items():
        other = name.split(" - ")[1]
        lines.append(f"| {LABELS.get(other, other)} | {c['mean']:+.3f} ({c['ci'][0]:+.3f} to {c['ci'][1]:+.3f}) | {c['n']:,} |")
    return lines


def _isolation(rep: dict) -> list[str]:
    ld = rep["load"]
    if not ld:
        return []
    f, n = ld["fair"], ld["none"]
    return [
        f"Measured capacity of the service and a one-node cluster on the CI runner: about **{ld['capacity_qps']:.0f} searches a second**. "
        "During the burst one shop's agent sends 1.6 times that, while the other three shops keep a steady trickle.",
        "",
        "| While one shop's agent bursts | Per-tenant admission | One shared queue |",
        "|---|---:|---:|",
        f"| Other shops' p50 latency, before the burst | {f['quiet_calm_p50_ms']:.0f} ms | {n['quiet_calm_p50_ms']:.0f} ms |",
        f"| Other shops' p99 latency, before the burst | {f['quiet_calm_p99_ms']:.0f} ms | {n['quiet_calm_p99_ms']:.0f} ms |",
        f"| Other shops' p50 latency, during the burst | **{f['quiet_burst_p50_ms']:.0f} ms** | {n['quiet_burst_p50_ms']:,.0f} ms |",
        f"| Other shops' p99 latency, during the burst | **{f['quiet_burst_p99_ms']:.0f} ms** | {n['quiet_burst_p99_ms']:,.0f} ms |",
        f"| Other shops' searches that failed during the burst | **{_pct(f['quiet_burst_failed'])}** | {_pct(n['quiet_burst_failed'])} |",
        f"| Agent's searches answered 429 (retry later) | {_pct(f['noisy_limited_share'])} | {_pct(n['noisy_limited_share'])} |",
        f"| Agent's searches that timed out or failed | {_pct(f['noisy_failed_share'])} | {_pct(n['noisy_failed_share'])} |",
    ]


def block(dev: dict, held: dict | None, gate_dev: dict | None, gate_held: dict | None) -> str:
    lines = [START, "", "### Dashboard (development worlds)", "", *_headline(dev, "Development"), ""]
    lines += [
        f"{len(dev['seeds'])} simulated worlds, each with {len(dev['tenants'])} shops and {dev['products']:,} products; "
        f"{dev['queries_per_seed']:,} graded queries a world, {dev['queries_per_seed'] * len(dev['seeds']):,} in all ("
        + ", ".join(f"{dev['shapes'][k]:,} {SHAPE_IN_TEXT[k]}" for k in SHAPE_LABELS if k in dev["shapes"])
        + ").",
        "",
        "![nDCG by query shape](reports/charts/shapes.svg)",
        "",
        "### Every design on the same queries",
        "",
        *_designs(dev),
        "",
        "### One shop's AI agent bursts",
        "",
        *_isolation(dev),
        "",
        "![Isolation](reports/charts/isolation.svg)",
    ]
    if gate_dev:
        lines += ["", f"Gate (`config/gate.yaml`) on the development worlds: **{'passed' if gate_dev['passed'] else 'failed'}**."]
    if held:
        lines += ["", "### Held-out worlds (run once)", "", *_headline(held, "Held-out"), "", *_isolation(held)]
        if gate_held:
            lines += ["", f"Gate on the held-out worlds: **{'passed' if gate_held['passed'] else 'failed'}**."]
    lines += ["", END]
    return "\n".join(lines)


def write_charts(dev: dict) -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    (CHARTS / "shapes.svg").write_text(chart_shapes(dev))
    if dev.get("load"):
        (CHARTS / "isolation.svg").write_text(chart_isolation(dev))


def render_readme(text: str, new_block: str) -> str:
    a, b = text.index(START), text.index(END) + len(END)
    return text[:a] + new_block + text[b:]


def readme_path() -> Path:
    return README
