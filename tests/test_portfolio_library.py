from pyfpa.config.schemas import EntityConfig
from pyfpa.portfolio.mine import PriorCandidate, SkillCandidate
from pyfpa.portfolio.validate import ValidationResult
from pyfpa.portfolio.library import (
    load_library, promote_prior, promote_skill, seed_from_library,
)


def _cfg(dio=30.0):
    return EntityConfig.model_validate({
        "name": "c", "start_month": "2026-01", "horizon_months": 12, "tax_rate": 0.0,
        "channels": [{"name": "C", "annual_revenue": 1_000_000.0, "growth_rate": 0.0,
                      "seasonality": [1.0] * 12, "cogs_pct": 0.5}],
        "opex": [], "debt": [],
        "working_capital": {"dso_days": 30.0, "dpo_days": 30.0, "dio_days": dio},
        "opening_balances": {"cash": 0.0},
    })


def test_promote_prior_and_seed(tmp_path):
    lib = tmp_path / "library"
    cand = PriorCandidate(business_type="d2c", driver="working_capital.dio_days",
                          value=45.0, support=["a", "b", "c"], dispersion=0.02)
    promote_prior(lib, cand, ValidationResult(mean_delta=-0.01, n_folds=3, validated=True))
    assert "working_capital.dio_days" in (lib / "library-log.md").read_text()
    seeded = seed_from_library(lib, "d2c", _cfg(dio=30.0))
    assert seeded.working_capital.dio_days == 45.0
    assert _cfg(dio=30.0).working_capital.dio_days == 30.0     # base unmutated


def test_seed_unknown_type_is_noop(tmp_path):
    lib = tmp_path / "library"
    out = seed_from_library(lib, "saas", _cfg(dio=30.0))
    assert out.working_capital.dio_days == 30.0


def test_promote_two_priors_same_type_appends(tmp_path):
    # a second prior for the same business-type must EXTEND the file, not overwrite
    lib = tmp_path / "library"
    val = ValidationResult(mean_delta=0.0, n_folds=3, validated=True)
    promote_prior(lib, PriorCandidate(business_type="d2c", driver="working_capital.dio_days",
                                      value=45.0, support=["a", "b", "c"], dispersion=0.02), val)
    promote_prior(lib, PriorCandidate(business_type="d2c", driver="tax_rate",
                                      value=0.25, support=["a", "b", "c"], dispersion=0.01), val)
    drivers = {p["driver"] for p in load_library(lib)["priors"]["d2c"]}
    assert drivers == {"working_capital.dio_days", "tax_rate"}


def test_load_library_round_trip(tmp_path):
    lib = tmp_path / "library"
    cand = PriorCandidate(business_type="d2c", driver="tax_rate", value=0.25,
                          support=["a", "b", "c"], dispersion=0.01)
    promote_prior(lib, cand, ValidationResult(mean_delta=0.0, n_folds=3, validated=True))
    loaded = load_library(lib)
    assert any(p["driver"] == "tax_rate" and p["value"] == 0.25 for p in loaded["priors"]["d2c"])


def test_promote_skill_copies_and_logs(tmp_path):
    src = tmp_path / "src" / "arr-waterfall"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text("---\nname: arr-waterfall\ndescription: x\n---\n")
    lib = tmp_path / "library"
    promote_skill(lib, SkillCandidate(business_type="saas", name="arr-waterfall",
                                      support=["a", "b", "c"], source=str(src)))
    assert (lib / "skills" / "arr-waterfall" / "SKILL.md").exists()
    assert "arr-waterfall" in (lib / "library-log.md").read_text()
