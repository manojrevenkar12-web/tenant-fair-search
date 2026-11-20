"""Keyed random streams: the same seed and keys give the same draws, whatever else runs before them."""

from __future__ import annotations

import hashlib

import numpy as np


def stream(seed: int, *keys: object) -> np.random.Generator:
    digest = hashlib.blake2b(repr((seed, *keys)).encode(), digest_size=8).digest()
    return np.random.default_rng(int.from_bytes(digest, "little"))
