"""Relevance measured against the world's hidden grades, and paired intervals over queries."""

from __future__ import annotations

import math

import numpy as np

from tfs.world.luck import stream


def dcg(gains: list[int], k: int) -> float:
    return sum((2**g - 1) / math.log2(i + 2) for i, g in enumerate(gains[:k]))


def ndcg(ranked: list[str], grades: dict[str, int], k: int = 10) -> float:
    ideal = dcg(sorted(grades.values(), reverse=True), k)
    if ideal == 0:
        return 0.0
    return dcg([grades.get(pid, 0) for pid in ranked], k) / ideal


def mean_ci(values: list[float], seed: int, key: str, draws: int = 2000) -> tuple[float, float, float]:
    """Mean with a 95% bootstrap interval."""
    x = np.asarray(values, dtype=float)
    if len(x) == 0:
        return (0.0, 0.0, 0.0)
    rng = stream(seed, "bootstrap", key)
    idx = rng.integers(0, len(x), size=(draws, len(x)))
    means = x[idx].mean(axis=1)
    return (float(x.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975)))


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(values, q)) if values else float("nan")
