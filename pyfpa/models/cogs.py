from __future__ import annotations

import pandas as pd

from pyfpa.config.schemas import EntityConfig


def cogs_from_config(cfg: EntityConfig, revenue_df: pd.DataFrame) -> pd.DataFrame:
    """Monthly COGS per channel (revenue * cogs_pct) + total."""
    data = {ch.name: revenue_df[ch.name] * ch.cogs_pct for ch in cfg.channels}
    df = pd.DataFrame(data, index=revenue_df.index)
    return df.assign(total=df.sum(axis=1))
