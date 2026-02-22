"""Context builder: fetches live DB data and formats it as text for AI chat."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database.models import Client, Transaction
from app.ledger.service import LedgerService
from app.utils.formatters import format_currency


class ChatContextBuilder:
    """Collects relevant data from DB and formats it as a readable context string."""

    def __init__(self, base_currency_code: str) -> None:
        self._base = base_currency_code.upper()
        self._ledger = LedgerService()

    async def build(self, session: AsyncSession) -> str:
        """Return a multi-section context string with current kassa state."""

        lines: list[str] = []

        # 1. Balances
        balances = await self._ledger.balance_by_currency(session)
        lines.append("БАЛАНС:")
        if balances:
            for code, amount in balances:
                lines.append(f"  {format_currency(amount, code)}")
        else:
            lines.append("  (пусто)")

        # 2. Today's summary
        today = date.today()
        start_dt = datetime.combine(today, time.min)
        end_dt = datetime.combine(today, time.max)

        count_result = await session.execute(
            select(Transaction).where(
                Transaction.created_at >= start_dt,
                Transaction.created_at <= end_dt,
            )
        )
        today_txs = list(count_result.scalars().all())
        lines.append(f"\nСегодняшние операции: {len(today_txs)} ")

        # 3. Last 5 transactions
        last_txs_result = await session.execute(
            select(Transaction)
            .options(
                joinedload(Transaction.from_currency),
                joinedload(Transaction.to_currency),
                joinedload(Transaction.client),
            )
            .order_by(Transaction.created_at.desc())
            .limit(5)
        )
        last_txs = list(last_txs_result.scalars().all())

        lines.append("\nПоследние операции:")
        if last_txs:
            for tx in last_txs:
                client_name = tx.client.name if tx.client else "неизвестно"
                
                # Format FROM and TO parts
                from_str = format_currency(tx.from_amount, tx.from_currency.code)
                to_str = format_currency(tx.to_amount, tx.to_currency.code)
                
                lines.append(
                    f"  #{tx.id} | {tx.created_at.strftime('%d.%m %H:%M')} | "
                    f"{from_str} → {to_str} | "
                    f"курс: {tx.rate:,.0f} | клиент: {client_name}"
                )
        else:
            lines.append("  (нет)")

        # 4. Last 5 clients
        clients_result = await session.execute(
            select(Client).order_by(Client.created_at.desc()).limit(5)
        )
        clients = list(clients_result.scalars().all())

        lines.append("\nПоследние клиенты:")
        if clients:
            for c in clients:
                no_phone = "телефон не указан"
                phone_str = c.phone if c.phone else no_phone
                lines.append(f"  #{c.id} {c.name} ({phone_str})")
        else:
            lines.append("  (нет)")

        # 5. Last hour transactions
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        hour_result = await session.execute(
            select(Transaction).where(Transaction.created_at >= one_hour_ago)
        )
        hour_txs = list(hour_result.scalars().all())
        lines.append(f"\nПоследние операции за 1 час: {len(hour_txs)} ")

        return "\n".join(lines)
