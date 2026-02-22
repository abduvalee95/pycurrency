"""Validation and normalization for AI parser output."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.api.errors import ValidationError
from app.schemas.ai import AIParsedEntry


CURRENCY_ALIASES = {
    "DOLLAR": "USD",
    "USDT": "USD",
    "SOM": "UZS",
    "SUM": "UZS",
    "RUBL": "RUB",
    "РУБ": "RUB",
    "SO'M": "UZS",
}


class AIParseValidator:
    """Domain validator that normalizes and verifies parser output."""

    def validate(self, payload: dict) -> AIParsedEntry:
        """Validate required fields and normalize aliases."""

        if not isinstance(payload, dict):
            raise ValidationError("AI parser output must be a JSON object")

        currency_code = str(payload.get("currency_code", "")).upper().strip()
        currency_code = CURRENCY_ALIASES.get(currency_code, currency_code)

        try:
            amount = Decimal(str(payload.get("amount")))
        except (InvalidOperation, TypeError) as exc:
            raise ValidationError("AI parsed amount must be numeric") from exc

        model_payload = {
            "amount": amount,
            "currency_code": currency_code,
            "flow_direction": payload.get("flow_direction", ""),
            "client_name": payload.get("client_name"),
            "note": payload.get("note"),
        }

        try:
            parsed = AIParsedEntry.model_validate(model_payload)
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(f"Invalid AI parsed data: {exc}") from exc

        return parsed
