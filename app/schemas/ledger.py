"""Ledger schemas."""

from datetime import datetime
from decimal import Decimal

from app.schemas.common import ORMBaseSchema


class LedgerEntryRead(ORMBaseSchema):
    """Read model for ledger entries."""

    id: int
    currency_id: int
    transaction_id: int
    amount: Decimal
    created_at: datetime
