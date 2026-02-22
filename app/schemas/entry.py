"""Cash entry schemas for simplified cashflow model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMBaseSchema


class EntryCreate(BaseModel):
    """Payload for creating a cash entry."""

    amount: Decimal = Field(gt=0, lt=Decimal("10000001"))  # max 10M per transaction
    currency_code: str = Field(min_length=3, max_length=3)
    flow_direction: str = Field(min_length=6, max_length=8)
    client_name: str = Field(min_length=1, max_length=128)
    note: Optional[str] = Field(default=None, max_length=512)

    @field_validator("client_name")
    @classmethod
    def normalize_client_name(cls, value: str) -> str:
        return value.strip().title()

    @field_validator("currency_code")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        from app.utils.currency import normalize_currency as _norm
        result = _norm(value)
        if result is None:
            raise ValueError("currency_code must be USD, RUB, UZS, KGS, or EUR")
        return result

    @field_validator("flow_direction")
    @classmethod
    def normalize_flow(cls, value: str) -> str:
        normalized = value.upper().strip()
        if normalized not in {"INFLOW", "OUTFLOW"}:
            raise ValueError("flow_direction must be INFLOW or OUTFLOW")
        return normalized


class EntryRead(ORMBaseSchema):
    """Response model for one cash entry."""

    id: int
    amount: Decimal
    currency_code: str
    flow_direction: str
    client_name: str
    note: Optional[str]
    created_by_telegram_id: int
    created_at: datetime


class EntryListResponse(BaseModel):
    """Paginated list of cash entries."""

    total: int
    items: list[EntryRead]
