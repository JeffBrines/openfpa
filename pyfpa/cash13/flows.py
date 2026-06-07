from __future__ import annotations

from pyfpa.cash13.schemas import WeeklyFlow


def expand_flow(flow: WeeklyFlow, weeks: int) -> list[float]:
    """Expand one WeeklyFlow into a length-`weeks` list (index 0 == week 1)."""
    amounts = [0.0] * weeks
    end = flow.end_week if flow.end_week is not None else weeks

    if flow.recurrence == "once":
        hit_weeks = [flow.start_week]
    elif flow.recurrence == "weekly":
        hit_weeks = range(flow.start_week, end + 1)
    else:  # biweekly
        hit_weeks = range(flow.start_week, end + 1, 2)

    for week in hit_weeks:
        if 1 <= week <= weeks:
            amounts[week - 1] += flow.amount
    return amounts
