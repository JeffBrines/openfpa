import pytest
from pyfpa.memory.corrections import (
    Override, Correction, save_correction, load_corrections,
)
from pyfpa.config.schemas import EntityConfig
from pyfpa.memory.corrections import apply_corrections


def _cfg():
    return EntityConfig.model_validate({
        "name": "T", "start_month": "2026-01", "horizon_months": 12, "tax_rate": 0.0,
        "channels": [{"name": "C", "annual_revenue": 1_200_000.0, "growth_rate": 0.0,
                      "seasonality": [1.0] * 12, "cogs_pct": 0.5}],
        "opex": [], "debt": [],
        "working_capital": {"dso_days": 30.0, "dpo_days": 30.0, "dio_days": 30.0},
        "opening_balances": {"cash": 0.0},
    })


def _correction():
    return Correction(
        slug="2026-06-08-december-seasonality",
        type="parametric",
        target="channels[*].seasonality[11]",
        status="applied",
        date="2026-06-08",
        override=Override(path="channels[*].seasonality[11]", value=2.0),
        notes="**Was off:** even spread.\n\n**Why:** [[business-profile#seasonality]]",
    )


def test_correction_round_trip(tmp_path):
    save_correction(_correction(), tmp_path)
    loaded = load_corrections(tmp_path)
    assert len(loaded) == 1
    c = loaded[0]
    assert c.slug == "2026-06-08-december-seasonality"
    assert c.type == "parametric"
    assert c.status == "applied"
    assert c.override == Override(path="channels[*].seasonality[11]", value=2.0)
    assert "Was off" in c.notes
    assert "[[business-profile#seasonality]]" in c.notes


def test_load_missing_dir_is_empty(tmp_path):
    assert load_corrections(tmp_path / "nope") == []


def test_structural_correction_has_no_override(tmp_path):
    c = Correction(slug="defrev", type="structural", target="revenue",
                   status="open", date="2026-06-08",
                   notes="**Was off:** double-counting deferred revenue.")
    save_correction(c, tmp_path)
    back = load_corrections(tmp_path)[0]
    assert back.type == "structural"
    assert back.override is None


def test_apply_parametric_override_returns_new_cfg():
    cfg = _cfg()
    corr = Correction(slug="dio", type="parametric", target="working_capital.dio_days",
                      status="applied", date="2026-06-08",
                      override=Override(path="working_capital.dio_days", value=45.0))
    out = apply_corrections(cfg, [corr])
    assert out.working_capital.dio_days == 45.0
    assert cfg.working_capital.dio_days == 30.0          # input unmutated


def test_apply_star_seasonality():
    cfg = _cfg()
    corr = Correction(slug="dec", type="parametric", target="channels[*].seasonality[11]",
                      status="applied", date="2026-06-08",
                      override=Override(path="channels[*].seasonality[11]", value=2.0))
    out = apply_corrections(cfg, [corr])
    assert out.channels[0].seasonality[11] == 2.0


def test_apply_ignores_open_structural_context():
    cfg = _cfg()
    corrections = [
        Correction(slug="a", type="parametric", target="working_capital.dio_days",
                   status="open", date="2026-06-08",
                   override=Override(path="working_capital.dio_days", value=99.0)),
        Correction(slug="b", type="structural", target="revenue", status="applied",
                   date="2026-06-08"),
        Correction(slug="c", type="context", target="revenue", status="applied",
                   date="2026-06-08"),
    ]
    out = apply_corrections(cfg, corrections)
    assert out.working_capital.dio_days == 30.0          # nothing applied
