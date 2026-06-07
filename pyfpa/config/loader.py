from __future__ import annotations

from pathlib import Path

import yaml

from pyfpa.config.schemas import EntityConfig


def load_config(path: str | Path) -> EntityConfig:
    """Load and validate an EntityConfig from a YAML file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config not found: {p}")
    with p.open() as f:
        raw = yaml.safe_load(f)
    return EntityConfig.model_validate(raw)
