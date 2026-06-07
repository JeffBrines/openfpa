from pyfpa.cash13.schemas import WeeklyFlow
from pyfpa.cash13.flows import expand_flow


def test_once_hits_single_week():
    f = WeeklyFlow(name="x", amount=200.0, start_week=3, recurrence="once")
    assert expand_flow(f, 5) == [0.0, 0.0, 200.0, 0.0, 0.0]


def test_weekly_spans_to_default_end():
    f = WeeklyFlow(name="x", amount=10.0, start_week=1, recurrence="weekly")
    assert expand_flow(f, 4) == [10.0, 10.0, 10.0, 10.0]


def test_weekly_respects_explicit_end():
    f = WeeklyFlow(name="x", amount=10.0, start_week=2, recurrence="weekly", end_week=3)
    assert expand_flow(f, 5) == [0.0, 10.0, 10.0, 0.0, 0.0]


def test_biweekly_every_other_week():
    f = WeeklyFlow(name="x", amount=5.0, start_week=1, recurrence="biweekly")
    assert expand_flow(f, 6) == [5.0, 0.0, 5.0, 0.0, 5.0, 0.0]


def test_start_week_beyond_horizon_is_empty():
    f = WeeklyFlow(name="x", amount=99.0, start_week=10, recurrence="once")
    assert expand_flow(f, 5) == [0.0, 0.0, 0.0, 0.0, 0.0]
