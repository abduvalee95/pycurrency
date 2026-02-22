"""Balance projection service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.ledger.service import LedgerService
from app.schemas.balance import BalanceResponse, CurrencyBalance


class BalanceService:
    """Facade around ledger-based balance computation."""

    def __init__(self) -> None:
        self._ledger_service = LedgerService()

    async def get_all_balances(self, session: AsyncSession) -> BalanceResponse:
        """Return list of balances by currency code."""

        rows = await self._ledger_service.balance_by_currency(session)
        return BalanceResponse(
            balances=[CurrencyBalance(currency_code=code, balance=balance) for code, balance in rows]
        )
