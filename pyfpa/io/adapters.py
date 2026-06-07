from __future__ import annotations

from pathlib import Path

from pyfpa.io.pl_csv import read_pl_csv

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def from_netsuite(*, fixture: str | Path | None = None) -> dict[str, float]:
    """Return a normalized {account: amount} trial balance from NetSuite.

    Without live credentials this reads the bundled synthetic fixture. To go
    live, query NetSuite via SuiteQL (OAuth 1.0a) and map rows to {account:
    amount}; credentials come from the host environment, never committed.
    """
    return read_pl_csv(fixture or _FIXTURES / "netsuite_pl.csv")


def from_quickbooks(*, fixture: str | Path | None = None) -> dict[str, float]:
    """Return a normalized {account: amount} P&L from QuickBooks.

    Fixture-backed by default; the live path calls the QuickBooks Online API
    with host-supplied OAuth credentials.
    """
    return read_pl_csv(fixture or _FIXTURES / "quickbooks_pl.csv")


def from_shopify(*, fixture: str | Path | None = None) -> dict[str, float]:
    """Return a normalized D2C ops summary from Shopify.

    Shopify is operational data (orders/payouts), not a full GL; this returns a
    channel-revenue summary. Fixture-backed by default; the live path calls the
    Shopify Admin API with a host-supplied access token.
    """
    return read_pl_csv(fixture or _FIXTURES / "shopify_summary.csv")
