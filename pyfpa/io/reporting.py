from __future__ import annotations

from pathlib import Path

import pandas as pd


_REQUIRED_COLUMNS = {"revenue", "ebitda", "net_income", "ending_cash"}


def _money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.0f}"


def to_briefing_md(
    forecast_df: pd.DataFrame,
    *,
    title: str = "Cash Flow Briefing",
    runway: dict | None = None,
) -> str:
    """Render a monthly forecast as a board-style markdown briefing.

    Expects columns: revenue, ebitda, net_income, ending_cash. If `runway`
    (the dict from cash13.runway_summary) is provided, a 13-week section is added.
    """
    missing = _REQUIRED_COLUMNS - set(forecast_df.columns)
    if missing:
        raise ValueError(f"forecast_df missing required columns: {sorted(missing)}")
    df = forecast_df
    lines = [f"# {title}", "", "## Headline", ""]
    lines += [
        f"- **Revenue:** {_money(df['revenue'].sum())}",
        f"- **EBITDA:** {_money(df['ebitda'].sum())}",
        f"- **Net income:** {_money(df['net_income'].sum())}",
        f"- **Ending cash:** {_money(df['ending_cash'].iloc[-1])}",
        "",
    ]

    if runway is not None:
        first_neg = runway["first_negative_week"]
        first_neg_text = f"week {first_neg}" if first_neg is not None else "none"
        lines += [
            "## 13-Week Cash Runway",
            "",
            f"- **Trough:** {_money(runway['min_cash'])} (week {runway['min_week']})",
            f"- **First negative week:** {first_neg_text}",
            "",
        ]

    lines += [
        "## Monthly",
        "",
        "| Month | Revenue | EBITDA | Ending Cash |",
        "|---|---|---|---|",
    ]
    for period, row in df.iterrows():
        lines.append(
            f"| {period} | {_money(row['revenue'])} | "
            f"{_money(row['ebitda'])} | {_money(row['ending_cash'])} |"
        )
    return "\n".join(lines) + "\n"


def forecast_to_excel(forecast_df: pd.DataFrame, path: str | Path) -> None:
    """Write a forecast DataFrame to an .xlsx workbook (sheet 'Forecast')."""
    forecast_df.to_excel(Path(path), sheet_name="Forecast")
