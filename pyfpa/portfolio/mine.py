from __future__ import annotations

import statistics
from pathlib import Path

from pydantic import BaseModel

from pyfpa.memory.corrections import load_corrections
from pyfpa.portfolio.manifest import ClientRef, Portfolio, clients_of_type
from pyfpa.portfolio.recover import best_snapshot

MINEABLE_DRIVERS = [
    "working_capital.dso_days", "working_capital.dio_days", "working_capital.dpo_days",
    "tax_rate", "da_monthly", "capex_monthly",
]


class PriorCandidate(BaseModel):
    business_type: str
    driver: str
    value: float
    support: list[str]
    dispersion: float


class SkillCandidate(BaseModel):
    business_type: str
    name: str
    support: list[str]
    source: str


def _get_by_path(data: dict, path: str) -> float | None:
    node = data
    for segment in path.split("."):
        if not isinstance(node, dict) or segment not in node:
            return None
        node = node[segment]
    return float(node) if isinstance(node, (int, float)) else None


def client_driver_value(client: ClientRef, driver: str) -> float | None:
    """The best-snapshot value for `driver`, overridden by an applied parametric
    correction on that exact path if one exists."""
    snap = best_snapshot(client.path)
    if snap is None:
        return None
    for c in load_corrections(Path(client.path) / ".fpa" / "corrections"):
        if c.status == "applied" and c.type == "parametric" and c.override and c.override.path == driver:
            return c.override.value
    return _get_by_path(snap.assumptions, driver)


def mine_priors(portfolio: Portfolio, business_type: str, *,
                min_support: int = 3, dispersion_max: float = 0.15) -> list[PriorCandidate]:
    """Drivers that cluster tightly (CoV <= dispersion_max) across >= min_support
    same-type clients become prior candidates at the median."""
    clients = clients_of_type(portfolio, business_type)
    out: list[PriorCandidate] = []
    for driver in MINEABLE_DRIVERS:
        present = [(c, v) for c in clients if (v := client_driver_value(c, driver)) is not None]
        if len(present) < min_support:
            continue
        values = [v for _, v in present]
        spread = statistics.pstdev(values)
        mean = statistics.fmean(values)
        # Coefficient of variation; a perfectly tight cluster (incl. unanimous zero,
        # where mean is 0) is the strongest possible signal → dispersion 0.
        cov = 0.0 if spread == 0 else (spread / abs(mean) if mean else float("inf"))
        if cov <= dispersion_max:
            out.append(PriorCandidate(
                business_type=business_type, driver=driver,
                value=statistics.median(values), support=[c.path for c, _ in present],
                dispersion=cov,
            ))
    return out


def find_recurring_skills(portfolio: Portfolio, business_type: str, *,
                          min_support: int = 3) -> list[SkillCandidate]:
    """Generated-skill directory names that recur across >= min_support same-type
    clients. (Structural corrections are an additional human signal the operator
    weighs in the skill, not a mechanical trigger here.)"""
    clients = clients_of_type(portfolio, business_type)
    by_name: dict[str, list[tuple[str, str]]] = {}
    for c in clients:
        generated = Path(c.path) / "skills" / "generated"
        if not generated.exists():
            continue
        for d in sorted(generated.iterdir()):
            if (d / "SKILL.md").exists():
                by_name.setdefault(d.name, []).append((c.path, str(d)))
    out: list[SkillCandidate] = []
    for name, refs in by_name.items():
        if len(refs) >= min_support:
            out.append(SkillCandidate(
                business_type=business_type, name=name,
                support=[p for p, _ in refs], source=refs[0][1],
            ))
    return out
