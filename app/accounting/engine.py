"""Core accounting engine enforcing double-entry transaction creation."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.errors import NotFoundError, ValidationError
from app.database.models import Client, Currency, Transaction
from app.ledger.service import LedgerService
from app.schemas.transaction import AIOperatorConfirmRequest, TransactionCreate
from app.services.client_service import ClientService
from app.validators.business import ensure_distinct_values, ensure_positive_decimal


class AccountingEngine:
    """Create transactions and immutable ledger entries atomically."""

    def __init__(self, base_currency_code: str) -> None:
        self.base_currency_code = base_currency_code.upper()
        self.ledger_service = LedgerService()
        self.client_service = ClientService()

    async def create_manual_transaction(self, session: AsyncSession, payload: TransactionCreate) -> Transaction:
        """Create transaction from manual form input."""

        ensure_positive_decimal(payload.to_amount, "to_amount")
        ensure_positive_decimal(payload.rate, "rate")
        ensure_distinct_values(payload.from_currency_code, payload.to_currency_code, "currency")

        from_currency, to_currency = await self._resolve_currencies(
            session=session,
            from_code=payload.from_currency_code,
            to_code=payload.to_currency_code,
        )

        from_amount = payload.to_amount * payload.rate
        client = await self._resolve_client(session, None, payload.client_name)

        return await self._create_transaction_and_ledger(
            session=session,
            from_currency=from_currency,
            to_currency=to_currency,
            from_amount=from_amount,
            to_amount=payload.to_amount,
            rate=payload.rate,
            client=client,
        )

    async def create_from_ai_confirmation(
        self,
        session: AsyncSession,
        payload: AIOperatorConfirmRequest,
    ) -> Transaction:
        """Convert AI-structured buy/sell intent into accounting transaction pair."""

        ensure_positive_decimal(payload.amount, "amount")
        if payload.rate is not None:
            ensure_positive_decimal(payload.rate, "rate")

        foreign_currency, base_currency = await self._resolve_currencies(
            session=session,
            from_code=payload.currency,
            to_code=self.base_currency_code,
        )

        client = None
        if payload.client_name:
            client = await self.client_service.get_or_create_by_name(session, payload.client_name)

        if payload.transaction_type == "BUY":
            # BUY means operator bought foreign currency and paid base currency.
            effective_rate = payload.rate
            if effective_rate is None:
                effective_rate = await self._get_latest_rate(
                    session=session,
                    from_currency_id=base_currency.id,
                    to_currency_id=foreign_currency.id,
                )

            return await self._create_transaction_and_ledger(
                session=session,
                from_currency=base_currency,
                to_currency=foreign_currency,
                from_amount=payload.amount * effective_rate,
                to_amount=payload.amount,
                rate=effective_rate,
                client=client,
            )

        # SELL means operator sold foreign currency and received base currency.
        effective_rate = payload.rate
        if effective_rate is None:
            effective_rate = await self._get_latest_rate(
                session=session,
                from_currency_id=foreign_currency.id,
                to_currency_id=base_currency.id,
            )

        return await self._create_transaction_and_ledger(
            session=session,
            from_currency=foreign_currency,
            to_currency=base_currency,
            from_amount=payload.amount,
            to_amount=payload.amount * effective_rate,
            rate=effective_rate,
            client=client,
        )

    async def _resolve_currencies(
        self,
        session: AsyncSession,
        from_code: str,
        to_code: str,
    ) -> tuple[Currency, Currency]:
        """Load currency rows for given codes."""

        codes = [from_code.upper(), to_code.upper()]
        result = await session.execute(select(Currency).where(Currency.code.in_(codes)))
        currencies = {currency.code: currency for currency in result.scalars().all()}

        if codes[0] not in currencies:
            raise NotFoundError(f"Currency not found: {codes[0]}")
        if codes[1] not in currencies:
            raise NotFoundError(f"Currency not found: {codes[1]}")
        return currencies[codes[0]], currencies[codes[1]]

    async def _resolve_client(
        self,
        session: AsyncSession,
        client_id: Optional[int],
        client_name: Optional[str],
    ) -> Optional[Client]:
        """Resolve optional client by id or lazily create by name."""

        if client_id is not None:
            result = await session.execute(select(Client).where(Client.id == client_id).limit(1))
            client = result.scalar_one_or_none()
            if client is None:
                raise NotFoundError(f"Client not found: {client_id}")
            return client

        if client_name:
            return await self.client_service.get_or_create_by_name(session=session, name=client_name)

        return None

    async def _create_transaction_and_ledger(
        self,
        session: AsyncSession,
        *,
        from_currency: Currency,
        to_currency: Currency,
        from_amount: Decimal,
        to_amount: Decimal,
        rate: Decimal,
        client: Optional[Client],
    ) -> Transaction:
        """Persist transaction and its immutable double-entry rows atomically."""

        transaction = Transaction(
            from_currency_id=from_currency.id,
            to_currency_id=to_currency.id,
            from_amount=from_amount,
            to_amount=to_amount,
            rate=rate,
            client_id=client.id if client else None,
        )
        session.add(transaction)
        await session.flush()

        await self.ledger_service.create_double_entries(
            session=session,
            transaction_id=transaction.id,
            from_currency_id=from_currency.id,
            to_currency_id=to_currency.id,
            from_amount=from_amount,
            to_amount=to_amount,
        )

        await session.commit()

        result = await session.execute(
            select(Transaction)
            .options(
                joinedload(Transaction.from_currency),
                joinedload(Transaction.to_currency),
                joinedload(Transaction.client),
            )
            .where(Transaction.id == transaction.id)
        )
        return result.scalar_one()

    async def _get_latest_rate(
        self,
        session: AsyncSession,
        from_currency_id: int,
        to_currency_id: int,
    ) -> Decimal:
        """Fetch the rate used in the last transaction between these currencies."""

        # Try exact match direction first
        query = (
            select(Transaction.rate)
            .where(
                Transaction.from_currency_id == from_currency_id,
                Transaction.to_currency_id == to_currency_id,
            )
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        result = await session.execute(query)
        rate = result.scalar_one_or_none()

        if rate is not None:
            return rate

        raise ValidationError("Rate is required for first-time transaction with this currency pair.")
