from __future__ import annotations

import pandas as pd

from pyfpa.config.schemas import EntityConfig
from pyfpa.models.periods import month_index


def debt_from_config(cfg: EntityConfig) -> pd.DataFrame:
    """Monthly interest, principal, and ending balance summed across all
    instruments. Term loans amortize by monthly_principal; LOCs are interest-only."""
    idx = month_index(cfg.start_month, cfg.horizon_months)
    interest = pd.Series(0.0, index=idx)
    principal = pd.Series(0.0, index=idx)
    ending = pd.Series(0.0, index=idx)

    # interest/principal/ending are locally-owned Series; in-place setitem
    # accumulation across instruments is intentional (no .assign equivalent).
    for inst in cfg.debt:
        balance = inst.opening_balance
        monthly_rate = inst.annual_rate / 12.0
        for period in idx:
            month_interest = balance * monthly_rate
            month_principal = (
                min(inst.monthly_principal, balance) if inst.kind == "term_loan" else 0.0
            )
            balance -= month_principal
            interest[period] += month_interest
            principal[period] += month_principal
            ending[period] += balance

    return pd.DataFrame(
        {"interest": interest, "principal": principal, "ending_debt": ending}, index=idx
    )
