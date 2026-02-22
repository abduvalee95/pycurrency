"""Operational reporting service."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import get_settings
from app.database.models import Transaction
from app.profit.service import ProfitService
from app.schemas.report import PeriodReport, ProfitReport


class ReportService:
    """Compose daily/monthly and profit reports."""

    def __init__(self, base_currency_code: str) -> None:
        self.base_currency_code = base_currency_code.upper()
        self.profit_service = ProfitService(base_currency_code=base_currency_code)

    async def daily_report(self, session: AsyncSession, target_date: date) -> PeriodReport:
        """Build daily operational report."""

        settings = get_settings()
        tz = ZoneInfo(settings.timezone)
        
        # Create aware datetimes in local time
        start_dt = datetime.combine(target_date, time.min, tzinfo=tz)
        end_dt = datetime.combine(target_date, time.max, tzinfo=tz)
        
        return await self._period_report(session, "daily", target_date, target_date, start_dt, end_dt)

    async def monthly_report(self, session: AsyncSession, year: int, month: int) -> PeriodReport:
        """Build month-level operational report."""

        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)
        return await self._period_report(session, "monthly", start_date, end_date, start_dt, end_dt)

    async def profit_report(
        self,
        session: AsyncSession,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
    ) -> ProfitReport:
        """Return weighted-average realized profit report."""

        return await self.profit_service.profit_report(session=session, start_at=start_at, end_at=end_at)

    async def _period_report(
        self,
        session: AsyncSession,
        period: str,
        from_date: date,
        to_date: date,
        start_dt: datetime,
        end_dt: datetime,
    ) -> PeriodReport:
        """Common implementation for daily/monthly summaries."""

        count_result = await session.execute(
            select(func.count(Transaction.id)).where(
                Transaction.created_at >= start_dt,
                Transaction.created_at <= end_dt,
            )
        )
        tx_count = int(count_result.scalar_one())

        tx_result = await session.execute(
            select(Transaction)
            .options(joinedload(Transaction.from_currency), joinedload(Transaction.to_currency))
            .where(Transaction.created_at >= start_dt, Transaction.created_at <= end_dt)
        )
        transactions = list(tx_result.scalars().all())

        turnover = Decimal("0")
        for tx in transactions:
            if tx.from_currency.code == self.base_currency_code:
                turnover += Decimal(tx.from_amount)
            elif tx.to_currency.code == self.base_currency_code:
                turnover += Decimal(tx.to_amount)

        profit = await self.profit_service.profit_report(session=session, start_at=start_dt, end_at=end_dt)

        return PeriodReport(
            period=period,
            from_date=from_date,
            to_date=to_date,
            transaction_count=tx_count,
            turnover_in_base=turnover,
            total_profit=profit.total_profit,
        )
