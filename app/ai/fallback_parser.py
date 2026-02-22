"""Deterministic fallback parser for simple cash entry messages."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Optional

from app.api.errors import ValidationError

CURRENCY_ALIASES: dict[str, str] = {
    "USD": "USD",
    "DOLLAR": "USD",
    "USDT": "USD",
    "RUB": "RUB",
    "RUBL": "RUB",
    "UZS": "UZS",
    "SUM": "UZS",
    "SOM": "UZS",
    "SO'M": "UZS",
}

CURRENCY_PATTERN = re.compile(r"\b(?:usd|dollar|usdt|rub|rubl|uzs|sum|som|so'm)\b", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")


class RuleBasedAIParser:
    """Simple parser used when provider is unavailable."""

    def parse(self, text: str) -> dict:
        cleaned = " ".join(text.strip().split())
        lowered = cleaned.lower()

        amount, rate = self._extract_amount_and_optional_rate(lowered)
        currency = self._extract_currency(lowered)
        flow = self._detect_flow(lowered)
        client_name = self._extract_client_name(cleaned)

        note: Optional[str] = None
        if rate is not None:
            note = f"rate: {_format_decimal(rate)}"

        return {
            "amount": amount,
            "currency_code": currency,
            "flow_direction": flow,
            "client_name": client_name,
            "note": note,
        }

    def _detect_flow(self, text: str) -> str:
        outflow_tokens = ["sotdim", "sell", "prodal", "продал", "otdal"]
        inflow_tokens = ["oldim", "sotib oldim", "buy", "kupil", "купил", "olдим"]

        if any(token in text for token in outflow_tokens):
            return "OUTFLOW"
        if any(token in text for token in inflow_tokens):
            return "INFLOW"
        return "INFLOW"

    def _extract_currency(self, text: str) -> str:
        match = CURRENCY_PATTERN.search(text)
        if not match:
            raise ValidationError("Currency not found in text")
        raw = match.group(0).upper()
        return CURRENCY_ALIASES.get(raw, raw)

    def _extract_amount_and_optional_rate(self, text: str) -> tuple[Decimal, Optional[Decimal]]:
        numbers = NUMBER_PATTERN.findall(text)
        if not numbers:
            raise ValidationError("Amount must be present in text")
        amount = Decimal(numbers[0].replace(",", "."))
        rate = Decimal(numbers[1].replace(",", ".")) if len(numbers) > 1 else None
        return amount, rate

    def _extract_client_name(self, text: str) -> Optional[str]:
        first_token = text.split(" ", 1)[0] if text else ""
        if not first_token or NUMBER_PATTERN.fullmatch(first_token.replace(",", ".")):
            return None
        token = re.sub(r"(ga|qa|ka)$", "", first_token, flags=re.IGNORECASE)
        token = token.strip(" ,.;:-")
        return token or None


def _format_decimal(value: Decimal) -> str:
    """Render Decimal in plain notation without scientific format."""

    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text
