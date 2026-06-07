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
