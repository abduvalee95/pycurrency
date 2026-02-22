"""Weighted-average realized profit service."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database.models import Transaction
from app.schemas.report import ProfitByCurrency, ProfitReport


@dataclass
class InventoryState:
    """Running inventory for one currency in base-currency terms."""

    quantity: Decimal = Decimal("0")
    cost_in_base: Decimal = Decimal("0")


class ProfitService:
    """Compute realized profit using weighted-average inventory model."""

    def __init__(self, base_currency_code: str) -> None:
        self.base_currency_code = base_currency_code.upper()

    async def profit_report(
        self,
        session: AsyncSession,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
    ) -> ProfitReport:
        """Calculate realized profit breakdown for buy/sell operations."""

        query = (
            select(Transaction)
            .options(
                joinedload(Transaction.from_currency),
                joinedload(Transaction.to_currency),
            )
            .order_by(Transaction.created_at.asc(), Transaction.id.asc())
        )
        if end_at is not None:
            query = query.where(Transaction.created_at <= end_at)

        result = await session.execute(query)
        transactions = list(result.scalars().all())

        inventory: dict[str, InventoryState] = defaultdict(InventoryState)
        realized: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

        for tx in transactions:
            from_code = tx.from_currency.code
            to_code = tx.to_currency.code

            if from_code == self.base_currency_code and to_code != self.base_currency_code:
                # Buy foreign currency: increase inventory quantity/cost.
                state = inventory[to_code]
                state.quantity += Decimal(tx.to_amount)
                state.cost_in_base += Decimal(tx.from_amount)
                continue

            if from_code != self.base_currency_code and to_code == self.base_currency_code:
                # Sell foreign currency: realize P&L by weighted average cost.
                state = inventory[from_code]
                sell_qty = Decimal(tx.from_amount)
                proceeds = Decimal(tx.to_amount)

                avg_cost = Decimal("0")
                if state.quantity > 0:
                    avg_cost = state.cost_in_base / state.quantity

                cost_of_sold = avg_cost * sell_qty
                profit = proceeds - cost_of_sold
                if start_at is None or tx.created_at >= start_at:
                    realized[from_code] += profit

                state.quantity -= sell_qty
                state.cost_in_base -= cost_of_sold

        breakdown = [
            ProfitByCurrency(currency=currency, profit_in_base=amount)
            for currency, amount in sorted(realized.items(), key=lambda x: x[0])
        ]
        total = sum((item.profit_in_base for item in breakdown), Decimal("0"))
        return ProfitReport(base_currency=self.base_currency_code, total_profit=total, breakdown=breakdown)
