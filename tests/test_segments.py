import pytest
from pyfpa.analysis.segments import Segment, segment_pnl, roll_up_segments, segments_to_channels


def _segs():
    return [
        Segment(name="PVG", annual_revenue=500_000.0, cogs_pct=0.7, opex=50_000.0),
        Segment(name="AAG", annual_revenue=300_000.0, cogs_pct=0.6, opex=40_000.0),
        Segment(name="SSG", annual_revenue=200_000.0, cogs_pct=0.65, opex=30_000.0),
    ]


def test_segment_pnl_columns_and_math():
    df = segment_pnl(_segs())
    assert list(df.index) == ["PVG", "AAG", "SSG"]
    pvg = df.loc["PVG"]
    assert pvg["revenue"] == 500_000.0
    assert pvg["cogs"] == 350_000.0
    assert pvg["gross_profit"] == 150_000.0
    assert pvg["gross_margin"] == pytest.approx(0.3)
    assert pvg["segment_income"] == 100_000.0


def test_segment_pnl_empty():
    df = segment_pnl([])
    assert df.empty


def test_roll_up_segments_totals():
    total = roll_up_segments(_segs())
    assert total["revenue"] == 1_000_000.0
    assert total["cogs"] == pytest.approx(350_000 + 180_000 + 130_000)
    assert total["gross_profit"] == pytest.approx(1_000_000 - 660_000)
    assert total["opex"] == 120_000.0
    assert total["segment_income"] == pytest.approx(340_000 - 120_000)


def test_segments_to_channels_preserves_revenue_and_cogs():
    channels = segments_to_channels(_segs())
    assert [c.name for c in channels] == ["PVG", "AAG", "SSG"]
    assert all(len(c.seasonality) == 12 for c in channels)
    pvg = channels[0]
    assert pvg.annual_revenue == 500_000.0
    assert pvg.cogs_pct == 0.7
    assert pvg.growth_rate == 0.0
