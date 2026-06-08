import pytest
from pyfpa.portfolio.manifest import ClientRef, Portfolio, load_portfolio, clients_of_type


def test_load_portfolio_missing_raises():
    with pytest.raises(FileNotFoundError):
        load_portfolio("/nonexistent/portfolio.yaml")


def test_load_portfolio_and_filter(tmp_path):
    (tmp_path / "p.yaml").write_text(
        "library: ~/.fpa/library\n"
        "clients:\n"
        "  - { path: ~/clients/acme, type: d2c-inventory }\n"
        "  - { path: ~/clients/haul, type: trucking }\n"
        "  - { path: ~/clients/peak, type: d2c-inventory }\n"
    )
    pf = load_portfolio(tmp_path / "p.yaml")
    assert pf.library == "~/.fpa/library"
    assert len(pf.clients) == 3
    d2c = clients_of_type(pf, "d2c-inventory")
    assert [c.path for c in d2c] == ["~/clients/acme", "~/clients/peak"]
    assert all(isinstance(c, ClientRef) for c in d2c)
