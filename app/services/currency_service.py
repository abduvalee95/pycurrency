"""Currency lookup service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import NotFoundError
from app.database.models import Currency


class CurrencyService:
    """Service for currency lookups and listing."""

    async def list_currencies(self, session: AsyncSession) -> list[Currency]:
        """List all available currencies sorted by code."""

        result = await session.execute(select(Currency).order_by(Currency.code.asc()))
        return list(result.scalars().all())

    async def get_by_code(self, session: AsyncSession, code: str) -> Currency:
        """Resolve a currency by ISO code."""

        result = await session.execute(select(Currency).where(Currency.code == code.upper()).limit(1))
        currency = result.scalar_one_or_none()
        if not currency:
            raise NotFoundError(f"Currency not found: {code}")
        return currency
