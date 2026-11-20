"""Reads the settings files. The world reads world.yaml and catalogue.yaml; the platform reads platform.json."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"


@cache
def world() -> dict:
    return yaml.safe_load((CONFIG / "world.yaml").read_text())


@cache
def catalogue() -> dict:
    return yaml.safe_load((CONFIG / "catalogue.yaml").read_text())


@cache
def platform() -> dict:
    return json.loads((CONFIG / "platform.json").read_text())


@cache
def gate() -> dict:
    return yaml.safe_load((CONFIG / "gate.yaml").read_text())


@cache
def heldout() -> dict:
    return yaml.safe_load((CONFIG / "heldout.yaml").read_text())
