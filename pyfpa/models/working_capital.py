from __future__ import annotations

import pandas as pd

from pyfpa.config.schemas import EntityConfig

_DAYS_PER_MONTH = 30.0


def working_capital_from_config(
    cfg: EntityConfig, revenue_df: pd.DataFrame, cogs_df: pd.DataFrame
) -> pd.DataFrame:
    """AR/AP/inventory balances and their cash impact (rising AR/inventory uses
    cash; rising AP frees cash). First-period delta is vs opening balances."""
    idx = revenue_df.index
    wc = cfg.working_capital
    opening = cfg.opening_balances

    ar = revenue_df["total"] * (wc.dso_days / _DAYS_PER_MONTH)
    ap = cogs_df["total"] * (wc.dpo_days / _DAYS_PER_MONTH)
    inventory = cogs_df["total"] * (wc.dio_days / _DAYS_PER_MONTH)

    df = pd.DataFrame({"ar": ar, "ap": ap, "inventory": inventory}, index=idx)
    df = df.assign(
        d_ar=df["ar"].diff().fillna(df["ar"] - opening.ar),
        d_ap=df["ap"].diff().fillna(df["ap"] - opening.ap),
        d_inventory=df["inventory"].diff().fillna(df["inventory"] - opening.inventory),
    )
    return df.assign(
        wc_cash_impact=(-df["d_ar"] + df["d_ap"] - df["d_inventory"])
    )
