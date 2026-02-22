"""Balance schemas."""

from decimal import Decimal

from pydantic import BaseModel


class CurrencyBalance(BaseModel):
    """Single currency balance projection."""

    currency_code: str
    balance: Decimal


class BalanceResponse(BaseModel):
    """List of balances grouped by currency."""

    balances: list[CurrencyBalance]
