from pathlib import Path
import pytest
from pyfpa.cash13.schemas import Cash13Config
from pyfpa.io.loaders import load_cash13_config

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_load_cash13_config():
    cfg = load_cash13_config(REPO_ROOT / "examples/ridgeline/cash13.yaml")
    assert isinstance(cfg, Cash13Config)
    assert cfg.weeks == 13
    assert len(cfg.receipts) == 4


def test_load_cash13_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_cash13_config(REPO_ROOT / "examples/nope.yaml")


# --- append to tests/test_io_loaders.py ---
import pyfpa  # noqa: E402


def test_io_public_exports():
    for name in ["load_cash13_config", "read_pl_csv", "to_briefing_md",
                 "forecast_to_excel"]:
        assert hasattr(pyfpa, name), f"missing public export: {name}"
