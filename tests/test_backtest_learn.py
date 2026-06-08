import pytest
from pyfpa.backtest.learn import magnitude_cap, persistent_miss, render_scorecard
from pyfpa.backtest.snapshot import Snapshot
from pyfpa.backtest.score import ScoreResult


def test_magnitude_cap_clamps_relative():
    assert magnitude_cap(100.0, 200.0, cap=0.25) == pytest.approx(125.0)
    assert magnitude_cap(100.0, 10.0, cap=0.25) == pytest.approx(75.0)
    assert magnitude_cap(100.0, 110.0, cap=0.25) == pytest.approx(110.0)
    assert magnitude_cap(0.0, 5.0, cap=0.25) == 5.0


def test_persistent_miss_requires_k_same_signed():
    assert persistent_miss([0.1, 0.2], k=2) is True
    assert persistent_miss([-0.1, -0.2], k=2) is True
    assert persistent_miss([0.1, -0.2], k=2) is False
    assert persistent_miss([0.2], k=2) is False
    assert persistent_miss([0.001, 0.001], k=2, threshold=0.01) is False


def test_render_scorecard_table():
    snaps = [
        Snapshot(label="2026-01", created="2026-02-01", assumptions={}, predicted={},
                 score=ScoreResult(fitness=0.05, per_line={"revenue": 0.02}, weights={})),
        Snapshot(label="2026-02", created="2026-03-01", assumptions={}, predicted={},
                 score=ScoreResult(fitness=0.03, per_line={"revenue": -0.01}, weights={})),
    ]
    md = render_scorecard(snaps)
    assert "| 2026-01 |" in md
    assert "| 2026-02 |" in md
    assert "fitness" in md.lower()
