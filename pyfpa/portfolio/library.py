from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from pyfpa.config.schemas import EntityConfig
from pyfpa.memory.paths import apply_override
from pyfpa.portfolio.mine import PriorCandidate, SkillCandidate
from pyfpa.portfolio.validate import ValidationResult


def _log(library: Path, line: str) -> None:
    library.mkdir(parents=True, exist_ok=True)
    log = library / "library-log.md"
    header = "" if log.exists() else "# Library Log\n\n"
    with log.open("a") as f:
        f.write(header + line + "\n")


def load_library(library: str | Path) -> dict:
    """Read the library: {'priors': {type: [prior dicts]}, 'skills': [names]}."""
    library = Path(library)
    priors: dict[str, list[dict]] = {}
    priors_dir = library / "priors"
    if priors_dir.exists():
        for f in sorted(priors_dir.glob("*.yaml")):
            doc = yaml.safe_load(f.read_text()) or {}
            priors[doc.get("type", f.stem)] = doc.get("priors", [])
    skills = sorted(p.name for p in (library / "skills").glob("*")) if (library / "skills").exists() else []
    return {"priors": priors, "skills": skills}


def promote_prior(library: str | Path, candidate: PriorCandidate, validation: ValidationResult) -> None:
    """Append a ratified prior to priors/<type>.yaml and log it."""
    library = Path(library)
    priors_dir = library / "priors"
    priors_dir.mkdir(parents=True, exist_ok=True)
    path = priors_dir / f"{candidate.business_type}.yaml"
    doc = yaml.safe_load(path.read_text()) if path.exists() else None
    doc = doc or {"type": candidate.business_type, "priors": []}
    doc["priors"].append({
        "driver": candidate.driver, "value": candidate.value, "support": candidate.support,
        "cross_client_holdout_delta": validation.mean_delta, "n_folds": validation.n_folds,
    })
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    _log(library, f"- prior `{candidate.driver}` = {candidate.value} for {candidate.business_type} "
                  f"(support {len(candidate.support)}, delta {validation.mean_delta:+.4f})")


def promote_skill(library: str | Path, candidate: SkillCandidate) -> None:
    """Copy a recurring generated skill into the library and log it."""
    library = Path(library)
    dest = library / "skills" / candidate.name
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(candidate.source, dest, dirs_exist_ok=True)
    _log(library, f"- skill `{candidate.name}` for {candidate.business_type} "
                  f"(support {len(candidate.support)})")


def seed_from_library(library: str | Path, business_type: str, cfg: EntityConfig) -> EntityConfig:
    """Apply the library's promoted priors for `business_type` to a starting config.
    Returns a NEW config (input unmutated). Priors are seeds; the per-client loop refines."""
    data = cfg.model_dump()
    for prior in load_library(library)["priors"].get(business_type, []):
        apply_override(data, prior["driver"], prior["value"])
    return EntityConfig.model_validate(data)
