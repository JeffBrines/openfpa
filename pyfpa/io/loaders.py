from __future__ import annotations

from pathlib import Path

import yaml

from pyfpa.cash13.schemas import Cash13Config
from pyfpa.analysis.sku import Sku


def load_cash13_config(path: str | Path) -> Cash13Config:
    """Load and validate a Cash13Config from a YAML file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"cash13 config not found: {p}")
    with p.open() as f:
        raw = yaml.safe_load(f)
    return Cash13Config.model_validate(raw)


def load_skus(path: str | Path) -> list[Sku]:
    """Load a list of Sku from a YAML file with a top-level `skus:` list."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"SKU file not found: {p}")
    with p.open() as f:
        raw = yaml.safe_load(f)
    return [Sku.model_validate(item) for item in raw["skus"]]
