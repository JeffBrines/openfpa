from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class ClientRef(BaseModel):
    path: str          # client workspace root (contains .fpa/ and skills/)
    type: str          # business-type tag (the clustering key)


class Portfolio(BaseModel):
    library: str
    clients: list[ClientRef]


def load_portfolio(path: str | Path) -> Portfolio:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"portfolio manifest not found: {p}")
    return Portfolio.model_validate(yaml.safe_load(p.read_text()))


def clients_of_type(portfolio: Portfolio, business_type: str) -> list[ClientRef]:
    return [c for c in portfolio.clients if c.type == business_type]
