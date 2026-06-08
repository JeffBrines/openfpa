import pytest
from pyfpa.analysis.segments import Segment, segment_pnl, roll_up_segments, segments_to_channels


def _segs():
    # net sales + adjusted-EBITDA margin per segment (the disclosed metrics)
    return [
        Segment(name="PVG", net_sales=488_143.0, ebitda_margin=0.1276),
        Segment(name="AAG", net_sales=470_013.0, ebitda_margin=0.1187),
        Segment(name="SSG", net_sales=509_165.0, ebitda_margin=0.2114),
    ]


def test_segment_pnl_columns_and_math():
    df = segment_pnl(_segs())
    assert list(df.index) == ["PVG", "AAG", "SSG"]
    assert list(df.columns) == ["net_sales", "adjusted_ebitda", "ebitda_margin"]
    pvg = df.loc["PVG"]
    assert pvg["net_sales"] == 488_143.0
    assert pvg["adjusted_ebitda"] == pytest.approx(488_143.0 * 0.1276)
    assert pvg["ebitda_margin"] == pytest.approx(0.1276)


def test_segment_pnl_empty():
    df = segment_pnl([])
    assert df.empty
    assert list(df.columns) == ["net_sales", "adjusted_ebitda", "ebitda_margin"]


def test_roll_up_segments_totals():
    total = roll_up_segments(_segs())
    expected_sales = 488_143.0 + 470_013.0 + 509_165.0
    expected_ebitda = 488_143.0 * 0.1276 + 470_013.0 * 0.1187 + 509_165.0 * 0.2114
    assert total["net_sales"] == pytest.approx(expected_sales)
    assert total["adjusted_ebitda"] == pytest.approx(expected_ebitda)
    # margin recomputed from totals (revenue-weighted), NOT averaged
    assert total["ebitda_margin"] == pytest.approx(expected_ebitda / expected_sales)


def test_roll_up_empty_is_zero():
    total = roll_up_segments([])
    assert total["net_sales"] == 0.0
    assert total["adjusted_ebitda"] == 0.0
    assert total["ebitda_margin"] == 0.0


def test_segments_to_channels_applies_consolidated_cogs():
    segs = _segs() + [Segment(name="GROW", net_sales=100_000.0, growth_rate=0.05, ebitda_margin=0.10)]
    channels = segments_to_channels(segs, cogs_pct=0.69)
    assert [c.name for c in channels] == ["PVG", "AAG", "SSG", "GROW"]
    assert all(len(c.seasonality) == 12 for c in channels)
    assert all(c.cogs_pct == 0.69 for c in channels)  # consolidated rate applied to all
    pvg = channels[0]
    assert pvg.annual_revenue == 488_143.0
    assert pvg.growth_rate == 0.0
    assert channels[3].growth_rate == 0.05  # non-default growth carried through
