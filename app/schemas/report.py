"""Report schemas for simplified cashflow model."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


# Legacy models kept for compile compatibility in deprecated modules.
class ProfitByCurrency(BaseModel):
    currency: str
    profit_in_base: Decimal


class ProfitReport(BaseModel):
    base_currency: str
    total_profit: Decimal
    breakdown: list[ProfitByCurrency]


class PeriodReport(BaseModel):
    period: str
    from_date: date
    to_date: date
    transaction_count: int
    turnover_in_base: Decimal
    total_profit: Decimal


class DailyProfitReport(BaseModel):
    """Daily per-currency net flow report."""

    date: date
    by_currency: dict[str, Decimal]


class CurrencyBalancesReport(BaseModel):
    """All-time balance by currency."""

    by_currency: dict[str, Decimal]


class ClientDebtItem(BaseModel):
    """Client debt row by currency."""

    client_name: str
    currency_code: str
    debt_amount: Decimal


class ClientDebtReport(BaseModel):
    """Client debt report (outflow - inflow)."""

    items: list[ClientDebtItem]


class CashTotalReport(BaseModel):
    """Cash total in vault by currency and explicit UZS total."""

    by_currency: dict[str, Decimal]
    uzs_total: Decimal


class ExportDailyCSVResponse(BaseModel):
    """CSV export response with generated files."""

    date: date
    entries_csv_path: str
    reports_csv_path: str
