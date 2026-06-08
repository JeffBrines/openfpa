from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

_COLUMNS = ["model", "actual", "variance", "variance_pct", "within_tolerance"]


def reconcile(
    model: Mapping[str, float],
    actual: Mapping[str, float],
    *,
    tolerance: float = 0.01,
) -> pd.DataFrame:
    """Compare modeled vs actual line items.

    ``variance = model - actual``, ``variance_pct = variance / actual``
    (0.0 when actual is 0). A line is within tolerance when
    ``|variance_pct| <= tolerance``, or when both values are 0.

    Parameters
    ----------
    model:
        Mapping of line-item name to modeled value.
    actual:
        Mapping of line-item name to actual value. Drives the output rows.
    tolerance:
        Fractional threshold for ``within_tolerance`` (default 1 %).

    Returns
    -------
    pd.DataFrame
        Indexed by line-item name with columns
        ``model, actual, variance, variance_pct, within_tolerance``.
    """
    rows = []
    for line in actual:
        m = float(model.get(line, 0.0))
        a = float(actual[line])
        variance = m - a
        variance_pct = (variance / a) if a else 0.0
        within = (m == a) if a == 0 else (abs(variance_pct) <= tolerance)
        rows.append({
            "line": line,
            "model": m,
            "actual": a,
            "variance": variance,
            "variance_pct": variance_pct,
            "within_tolerance": within,
        })
    return pd.DataFrame(rows).set_index("line")[_COLUMNS]
