from __future__ import annotations

import pandas as pd

from pyfpa.config.schemas import EntityConfig


def opex_from_config(cfg: EntityConfig, revenue_df: pd.DataFrame) -> pd.DataFrame:
    """Monthly opex per line + total. Fixed lines are constant; variable lines
    scale with total revenue."""
    idx = revenue_df.index
    cols: dict[str, pd.Series] = {}
    for line in cfg.opex:
        if line.kind == "fixed":
            cols[line.name] = pd.Series(line.monthly_amount, index=idx, dtype="float64")
        else:  # variable
            cols[line.name] = revenue_df["total"] * line.pct_of_revenue
    df = pd.DataFrame(cols, index=idx)
    return df.assign(total=df.sum(axis=1))
