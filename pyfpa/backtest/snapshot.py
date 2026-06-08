from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd
import yaml
from pydantic import BaseModel

from pyfpa.config.schemas import EntityConfig
from pyfpa.backtest.score import DEFAULT_SCORE_LINES, ScoreResult, extract_lines


class Snapshot(BaseModel):
    """The full record of one forecast: the assumptions it used, the lines it
    predicted, and (once the period closes) the realized score."""

    label: str
    created: str                  # caller-supplied date string; never generated here
    assumptions: dict             # serialized EntityConfig
    predicted: dict[str, float]
    score: ScoreResult | None = None


def snapshot_forecast(
    cfg: EntityConfig,
    forecast_df: pd.DataFrame,
    *,
    label: str,
    created: str,
    score_lines: Sequence[str] = DEFAULT_SCORE_LINES,
) -> Snapshot:
    """Capture a forecast snapshot from an EntityConfig and its computed DataFrame."""
    return Snapshot(
        label=label,
        created=created,
        assumptions=cfg.model_dump(),
        predicted=extract_lines(forecast_df, score_lines),
    )


def save_snapshot(snapshot: Snapshot, path: str | Path) -> None:
    """Serialize a Snapshot to YAML at the given path."""
    Path(path).write_text(yaml.safe_dump(snapshot.model_dump(), sort_keys=False))


def load_snapshot(path: str | Path) -> Snapshot:
    """Deserialize a Snapshot from a YAML file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"snapshot not found: {p}")
    return Snapshot.model_validate(yaml.safe_load(p.read_text()))
