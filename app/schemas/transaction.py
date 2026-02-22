"""Transaction schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.database.models import TransactionType
from app.schemas.client import ClientRead
from app.schemas.common import ORMBaseSchema


class TransactionCreate(BaseModel):
    """Payload for creating a new transaction."""

    from_currency_code: str = Field(min_length=3, max_length=3)
    to_currency_code: str = Field(min_length=3, max_length=3)
    to_amount: Decimal = Field(gt=0)
    rate: Decimal = Field(gt=0)
    client_name: Optional[str] = Field(default=None, max_length=128)

    @field_validator("from_currency_code", "to_currency_code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.upper()


class TransactionRead(ORMBaseSchema):
    """Response model for a transaction."""

    id: int
    from_currency_code: str
    to_currency_code: str
    from_amount: Decimal
    to_amount: Decimal
    rate: Decimal
    created_at: datetime

    client: Optional[ClientRead]


class TransactionHistoryResponse(BaseModel):
    """Paginated transaction history response."""

    total: int
    items: list[TransactionRead]


class AIOperatorConfirmRequest(BaseModel):
    """Payload confirmed by operator after AI parsing."""

    transaction_type: TransactionType
    client_name: Optional[str] = None
    currency: str
    amount: Decimal = Field(gt=0)
    rate: Optional[Decimal] = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        """Normalize ISO code style."""

        return value.upper().strip()
