from pathlib import Path
import pytest
from pyfpa.io.pl_csv import read_pl_csv

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_read_pl_csv_parses_amounts(tmp_path):
    csv_path = tmp_path / "pl.csv"
    csv_path.write_text(
        "Account,Amount\n"
        'Revenue,"$6,000,000"\n'
        'COGS,"($2,940,000)"\n'
        "Blank,\n"
        ",999\n"  # blank account -> skipped
    )
    result = read_pl_csv(csv_path)
    assert result["Revenue"] == 6_000_000.0
    assert result["COGS"] == -2_940_000.0
    assert result["Blank"] == 0.0
    assert "" not in result  # blank-account row skipped


def test_read_pl_csv_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        read_pl_csv(REPO_ROOT / "examples/nope.csv")


def test_read_pl_csv_bad_columns_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Name,Value\nx,1\n")
    with pytest.raises(ValueError):
        read_pl_csv(bad)


def test_read_ridgeline_sample():
    result = read_pl_csv(REPO_ROOT / "examples/ridgeline/quickbooks_pl_sample.csv")
    assert result["Product Revenue"] == 6_000_000.0
    assert result["Cost of Goods Sold"] == -2_940_000.0
