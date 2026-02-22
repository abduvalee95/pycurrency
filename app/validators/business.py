"""Domain validation helpers."""

from decimal import Decimal

from app.api.errors import ValidationError


def ensure_positive_decimal(value: Decimal, field_name: str) -> None:
    """Validate that a decimal value is strictly positive."""

    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than 0")


def ensure_distinct_values(left: str, right: str, field_name: str) -> None:
    """Validate that two values are not equal."""

    if left == right:
        raise ValidationError(f"{field_name} values must be different")
