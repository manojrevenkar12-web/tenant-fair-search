"""Learns one tenant's term vectors from that tenant's own catalogue and search-to-purchase history.

A word gets a vector from the products it appears with: in product text, and in the queries that ended in a
purchase. "raincoat" never appears in a product title, but shoppers who typed it bought rain jackets, so it lands
next to "rain" and "jacket". Nothing crosses tenants: each model is trained only on its own shop's data.

The tokenizer is the platform's rule from config/platform.json; the Scala service embeds with the same rule and
both test suites check tests/fixtures/tokenize.json.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

from tfs import settings


class Tokenizer:
    def __init__(self) -> None:
        text = settings.platform()["text"]
        self.pattern = re.compile(text["tokenPattern"])
        self.stop = set(text["stopwords"])
        self.min_len = text["minTokenLength"]

    def __call__(self, text: str) -> list[str]:
        return [t for t in self.pattern.findall(text.lower()) if len(t) >= self.min_len and t not in self.stop]


def train(tenant: str, feed: list[dict], logs: list[tuple[str, str]]) -> dict:
    """Returns the model the service loads: {tenant, dim, idf, terms}."""
    cfg = settings.platform()["embedding"]
    dim = cfg["dim"]
    tok = Tokenizer()
    keep = (lambda t: not t.isdigit()) if cfg["dropNumeric"] else (lambda t: True)

    index = {p["id"]: i for i, p in enumerate(feed)}
    rows: list[Counter] = []
    df: Counter = Counter()
    for p in feed:
        title = [t for t in tok(p["title"] + " " + p["brand"]) if keep(t)]
        body = [t for t in tok(p["description"]) if keep(t)]
        c: Counter = Counter()
        for t in title:
            c[t] += cfg["titleWeight"]
        for t in body:
            c[t] += 1.0
        rows.append(c)
        df.update(set(title) | set(body))

    for text, pid in logs:
        i = index.get(pid)
        if i is None:
            continue
        for t in tok(text):
            if keep(t):
                rows[i][t] += cfg["logWeight"]

    vocab = sorted({t for c in rows for t in c})
    term_ix = {t: j for j, t in enumerate(vocab)}
    m = np.zeros((len(vocab), len(feed)))
    for i, c in enumerate(rows):
        for t, v in c.items():
            m[term_ix[t], i] = v

    # Positive pointwise mutual information, then a truncated SVD.
    total = m.sum()
    pt = m.sum(axis=1, keepdims=True) / total
    pp = m.sum(axis=0, keepdims=True) / total
    with np.errstate(divide="ignore", invalid="ignore"):
        pmi = np.log((m / total) / (pt * pp))
    ppmi = np.where(np.isfinite(pmi) & (pmi > 0), pmi, 0.0)
    u, s, _ = np.linalg.svd(ppmi, full_matrices=False)
    vectors = u[:, :dim] * np.sqrt(s[:dim])
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = np.divide(vectors, norms, out=np.zeros_like(vectors), where=norms > 0)

    n = len(feed)
    idf = {t: round(float(np.log((1 + n) / (1 + df.get(t, 0))) + 1.0), 6) for t in vocab}
    terms = {t: [round(float(x), 6) for x in vectors[term_ix[t]]] for t in vocab if norms[term_ix[t], 0] > 0}
    return {"tenant": tenant, "dim": dim, "idf": idf, "terms": terms}


def write(model: dict, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{model['tenant']}.json"
    path.write_text(json.dumps(model, separators=(",", ":")))
    return path


def cosine(model: dict, a: str, b: str) -> float:
    va, vb = np.array(model["terms"][a]), np.array(model["terms"][b])
    return float(va @ vb)
