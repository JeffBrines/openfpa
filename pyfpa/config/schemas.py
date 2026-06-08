from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, field_validator


class Channel(BaseModel):
    name: str
    annual_revenue: float = Field(ge=0)
    growth_rate: float = 0.0          # annual YoY, compounded per forecast year
    seasonality: list[float] = Field(min_length=12, max_length=12)
    cogs_pct: float = Field(ge=0, le=1)

    @field_validator("name")
    @classmethod
    def _name_not_reserved(cls, v: str) -> str:
        if v.strip().lower() == "total":
            raise ValueError("'total' is a reserved column name")
        return v

    @field_validator("seasonality")
    @classmethod
    def _weights_positive(cls, v: list[float]) -> list[float]:
        if sum(v) <= 0:
            raise ValueError("seasonality weights must sum to a positive number")
        return v


class OpexLine(BaseModel):
    name: str
    kind: Literal["fixed", "variable"]
    monthly_amount: float = 0.0       # used when kind == "fixed"
    pct_of_revenue: float = 0.0       # used when kind == "variable"

    @field_validator("name")
    @classmethod
    def _name_not_reserved(cls, v: str) -> str:
        if v.strip().lower() == "total":
            raise ValueError("'total' is a reserved column name")
        return v


class DebtInstrument(BaseModel):
    name: str
    kind: Literal["term_loan", "loc"]
    opening_balance: float = Field(ge=0)
    annual_rate: float = Field(ge=0)
    monthly_principal: float = Field(default=0.0, ge=0)  # term_loan only


class WorkingCapitalConfig(BaseModel):
    dso_days: float = Field(ge=0)
    dpo_days: float = Field(ge=0)
    dio_days: float = Field(ge=0)


class OpeningBalances(BaseModel):
    cash: float = 0.0
    ar: float = 0.0
    ap: float = 0.0
    inventory: float = 0.0
    nol: float = Field(default=0.0, ge=0)  # net operating loss carryforward


class EntityConfig(BaseModel):
    name: str
    start_month: str
    horizon_months: int = Field(default=12, ge=1, le=120)
    tax_rate: float = Field(default=0.21, ge=0, le=1)
    da_monthly: float = Field(default=0.0, ge=0)      # depreciation & amortization
    capex_monthly: float = Field(default=0.0, ge=0)   # capital expenditure
    channels: list[Channel]
    opex: list[OpexLine] = Field(default_factory=list)
    debt: list[DebtInstrument] = Field(default_factory=list)
    working_capital: WorkingCapitalConfig
    opening_balances: OpeningBalances = Field(default_factory=OpeningBalances)

    @field_validator("start_month")
    @classmethod
    def _valid_month(cls, v: str) -> str:
        try:
            pd.Period(v, freq="M")
        except Exception as e:  # noqa: BLE001 - re-raised as ValueError for pydantic
            raise ValueError(f"start_month must be YYYY-MM, got {v!r}") from e
        return v
