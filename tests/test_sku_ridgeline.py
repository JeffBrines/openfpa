from pathlib import Path
from pyfpa.io.loaders import load_skus
from pyfpa.analysis.sku import sku_profitability, pareto_breakpoint

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_load_and_analyze_ridgeline_skus():
    skus = load_skus(REPO_ROOT / "examples/ridgeline/skus.yaml")
    assert len(skus) == 5
    df = sku_profitability(skus)
    assert len(df) == 5
    # cumulative reaches exactly 1.0 at the end
    assert round(df["cumulative_revenue_pct"].iloc[-1], 6) == 1.0
    # a small SKU set: a few products carry most of the margin
    assert 1 <= pareto_breakpoint(df, 0.8) <= 5
