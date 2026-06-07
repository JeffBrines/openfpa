import pandas as pd
from pyfpa.models.periods import month_index


def test_month_index_length_and_start():
    idx = month_index("2026-01", 12)
    assert len(idx) == 12
    assert idx[0] == pd.Period("2026-01", freq="M")
    assert idx[-1] == pd.Period("2026-12", freq="M")


def test_month_index_crosses_year_boundary():
    idx = month_index("2026-11", 3)
    assert list(idx) == [
        pd.Period("2026-11", freq="M"),
        pd.Period("2026-12", freq="M"),
        pd.Period("2027-01", freq="M"),
    ]
