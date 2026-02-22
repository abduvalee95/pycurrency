"""Oddiy pul oqimi amaliyotlari modeli uchun AI parsing sxemalari."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AIParseRequest(BaseModel):
    """Tizim tushunadigan shaklga o'girish uchun operatordan olingan xom (raw) matn."""

    text: str = Field(min_length=2, max_length=500)


class AIParsedEntry(BaseModel):
    """Yozuv (entry) yaratish uchun validatsiyadan o'tgan AI parsing natijasi."""

    amount: Decimal
    currency_code: str
    flow_direction: str
    client_name: Optional[str] = None
    note: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("amount must be positive")
        return value

    @field_validator("currency_code")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized = value.upper().strip()
        if normalized not in {"USD", "RUB", "UZS"}:
            raise ValueError("currency_code must be USD, RUB, or UZS")
        return normalized

    @field_validator("flow_direction")
    @classmethod
    def validate_flow(cls, value: str) -> str:
        normalized = value.upper().strip()
        if normalized not in {"INFLOW", "OUTFLOW"}:
            raise ValueError("flow_direction must be INFLOW or OUTFLOW")
        return normalized

    @field_validator("client_name")
    @classmethod
    def normalize_client(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None
