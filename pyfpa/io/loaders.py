from __future__ import annotations

from pathlib import Path

import yaml

from pyfpa.cash13.schemas import Cash13Config


def load_cash13_config(path: str | Path) -> Cash13Config:
    """Load and validate a Cash13Config from a YAML file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"cash13 config not found: {p}")
    with p.open() as f:
        raw = yaml.safe_load(f)
    return Cash13Config.model_validate(raw)
