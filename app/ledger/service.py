"""Ledger-related business logic."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Currency, LedgerEntry


class LedgerService:
    """Service focused on immutable ledger operations and projections."""

    async def create_double_entries(
        self,
        session: AsyncSession,
        *,
        transaction_id: int,
        from_currency_id: int,
        to_currency_id: int,
        from_amount: Decimal,
        to_amount: Decimal,
    ) -> list[LedgerEntry]:
        """Create immutable debit/credit pair for an exchange transaction."""

        entries = [
            LedgerEntry(currency_id=from_currency_id, transaction_id=transaction_id, amount=-abs(from_amount)),
            LedgerEntry(currency_id=to_currency_id, transaction_id=transaction_id, amount=abs(to_amount)),
        ]
        session.add_all(entries)
        await session.flush()
        return entries

    async def balance_by_currency(self, session: AsyncSession) -> list[tuple[str, Decimal]]:
        """Compute balances from ledger sums grouped by currency code."""

        query = (
            select(Currency.code, func.coalesce(func.sum(LedgerEntry.amount), 0))
            .outerjoin(LedgerEntry, LedgerEntry.currency_id == Currency.id)
            .group_by(Currency.code)
            .order_by(Currency.code.asc())
        )
        result = await session.execute(query)
        return [(code, balance) for code, balance in result.all()]

    async def balance_for_currency(self, session: AsyncSession, currency_code: str) -> Decimal:
        """Compute current dynamic balance for one currency."""

        query = (
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .join(Currency, Currency.id == LedgerEntry.currency_id)
            .where(Currency.code == currency_code.upper())
        )
        result = await session.execute(query)
        return result.scalar_one()
