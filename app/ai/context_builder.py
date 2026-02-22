"""Context builder: fetches live DB data and formats it as text for AI chat."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Union

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CashEntry


def _fmt(value: Union[Decimal, int, float], currency: str) -> str:
    """Format currency amount for display."""
    return f"{Decimal(value):,.2f} {currency}".replace(",", " ")


class ChatContextBuilder:
    """Collects relevant data from CashEntry table and formats it as readable context for AI."""

    def __init__(self, base_currency_code: str) -> None:
        self._base = base_currency_code.upper()

    async def build(self, session: AsyncSession) -> str:
        """Return a multi-section context string with current kassa state."""

        lines: list[str] = []

        # 1. Balances by currency (INFLOW - OUTFLOW)
        net_case = case(
            (CashEntry.flow_direction == "INFLOW", CashEntry.amount),
            else_=-CashEntry.amount,
        )
        balance_query = select(
            CashEntry.currency_code,
            func.coalesce(func.sum(net_case), 0),
        ).group_by(CashEntry.currency_code)

        result = await session.execute(balance_query)
        balances = {code: amount for code, amount in result.all()}

        lines.append("BALANS (valyuta bo'yicha):")
        if balances:
            for code in sorted(balances):
                lines.append(f"  {_fmt(balances[code], code)}")
        else:
            lines.append("  (bo'sh)")

        # 2. Today's entries count
        today = date.today()
        start_dt = datetime.combine(today, time.min)
        end_dt = datetime.combine(today, time.max)

        count_result = await session.execute(
            select(func.count(CashEntry.id)).where(
                CashEntry.created_at >= start_dt,
                CashEntry.created_at <= end_dt,
            )
        )
        today_count = count_result.scalar_one()
        lines.append(f"\nBugungi operatsiyalar soni: {today_count}")

        # 3. Today's net by currency
        today_net_result = await session.execute(
            select(
                CashEntry.currency_code,
                func.coalesce(func.sum(net_case), 0),
            )
            .where(CashEntry.created_at >= start_dt, CashEntry.created_at <= end_dt)
            .group_by(CashEntry.currency_code)
        )
        today_net = {code: amount for code, amount in today_net_result.all()}

        lines.append("\nBugungi kunlik foyda (valyuta bo'yicha):")
        if today_net:
            for code in sorted(today_net):
                lines.append(f"  {_fmt(today_net[code], code)}")
        else:
            lines.append("  (bugun operatsiya yo'q)")

        # 4. Last 10 entries
        last_entries_result = await session.execute(
            select(CashEntry)
            .order_by(CashEntry.created_at.desc())
            .limit(10)
        )
        last_entries = list(last_entries_result.scalars().all())

        lines.append("\nSo'nggi operatsiyalar:")
        if last_entries:
            for entry in last_entries:
                direction = "📥 KIRIM" if entry.flow_direction == "INFLOW" else "📤 CHIQIM"
                note_str = f" | izoh: {entry.note}" if entry.note else ""
                lines.append(
                    f"  #{entry.id} | {entry.created_at.strftime('%d.%m %H:%M')} | "
                    f"{direction} | {_fmt(entry.amount, entry.currency_code)} | "
                    f"mijoz: {entry.client_name}{note_str}"
                )
        else:
            lines.append("  (yo'q)")

        # 5. Client debts (outflow - inflow per client per currency)
        debt_case = case(
            (CashEntry.flow_direction == "OUTFLOW", CashEntry.amount),
            else_=-CashEntry.amount,
        )
        debt_query = (
            select(
                CashEntry.client_name,
                CashEntry.currency_code,
                func.coalesce(func.sum(debt_case), 0),
            )
            .group_by(CashEntry.client_name, CashEntry.currency_code)
            .order_by(CashEntry.client_name.asc())
        )
        debt_result = await session.execute(debt_query)
        debts = [(client, currency, amount) for client, currency, amount in debt_result.all()]

        lines.append("\nMijoz bo'yicha qarz:")
        if debts:
            for client, currency, amount in debts[:10]:
                lines.append(f"  {client} [{currency}]: {_fmt(amount, currency)}")
        else:
            lines.append("  (yo'q)")

        return "\n".join(lines)
