import pytest
from pyfpa.memory.corrections import (
    Override, Correction, save_correction, load_corrections,
)


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
