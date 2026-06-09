from __future__ import annotations

import pandas as pd

from pyfpa.cash13.flows import expand_flow
from pyfpa.cash13.schemas import Cash13Config, WeeklyFlow


def _sum_flows(flows: list[WeeklyFlow], weeks: int) -> list[float]:
    """Sum each flow's weekly amounts into a single length-`weeks` list."""
    totals = [0.0] * weeks
    for flow in flows:
        for i, amount in enumerate(expand_flow(flow, weeks)):
            totals[i] += amount
    return totals


def cash13_forecast(cfg: Cash13Config) -> pd.DataFrame:
    """Weekly direct-method cash forecast: receipts, disbursements, net, and
    cumulative ending cash. Raw cash position - no auto-draws."""
    weeks = cfg.weeks
    receipts = _sum_flows(cfg.receipts, weeks)
    disbursements = _sum_flows(cfg.disbursements, weeks)
    net_cash = [r - d for r, d in zip(receipts, disbursements)]

    ending_cash = []
    balance = cfg.opening_cash
    for n in net_cash:
        balance += n
        ending_cash.append(balance)

    idx = pd.RangeIndex(start=1, stop=weeks + 1, name="week")
    return pd.DataFrame(
        {
            "receipts": receipts,
            "disbursements": disbursements,
            "net_cash": net_cash,
            "ending_cash": ending_cash,
        },
        index=idx,
    )
