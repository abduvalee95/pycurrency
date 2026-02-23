"""Service layer for simplified cash entries and reports."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.models import CashEntry
from app.schemas.entry import EntryCreate


# Reusable filter to exclude soft-deleted entries
_not_deleted = CashEntry.deleted_at.is_(None)


class EntryService:
    """Create/list entries and compute cashflow reports."""

    async def create_entry(
        self,
        session: AsyncSession,
        payload: EntryCreate,
        created_by_telegram_id: int,
    ) -> CashEntry:
        """Persist one cash entry."""

        async with session.begin():
            entry = CashEntry(
                amount=payload.amount,
                currency_code=payload.currency_code,
                flow_direction=payload.flow_direction,
                client_name=payload.client_name,
                note=payload.note,
                created_by_telegram_id=created_by_telegram_id,
            )
            session.add(entry)
            await session.flush()
            await session.refresh(entry)
            return entry

    async def get_entry_by_id(self, session: AsyncSession, entry_id: int) -> Optional[CashEntry]:
        """Get a single active (non-deleted) entry by ID."""

        result = await session.execute(
            select(CashEntry).where(CashEntry.id == entry_id, _not_deleted)
        )
        return result.scalar_one_or_none()

    async def soft_delete_entry(self, session: AsyncSession, entry_id: int, user_id: int) -> Optional[CashEntry]:
        """Soft delete an entry by setting deleted_at. Returns the entry or None if not found.
        Uses pessimistic locking to prevent concurrency issues."""

        async with session.begin():
            result = await session.execute(
                select(CashEntry).where(CashEntry.id == entry_id, _not_deleted).with_for_update()
            )
            entry = result.scalar_one_or_none()
            if entry is None:
                return None
            entry.deleted_at = datetime.utcnow()
            entry.updated_by_telegram_id = user_id
            await session.flush()
            await session.refresh(entry)
            return entry

    async def restore_entry(self, session: AsyncSession, entry_id: int, user_id: int) -> Optional[CashEntry]:
        """Restore a soft-deleted entry by clearing deleted_at.
        Uses pessimistic locking."""

        async with session.begin():
            result = await session.execute(
                select(CashEntry).where(
                    CashEntry.id == entry_id,
                    CashEntry.deleted_at.is_not(None),
                ).with_for_update()
            )
            entry = result.scalar_one_or_none()
            if entry is None:
                return None
            entry.deleted_at = None
            entry.updated_by_telegram_id = user_id
            await session.flush()
            await session.refresh(entry)
            return entry

    async def list_entries(
        self,
        session: AsyncSession,
        *,
        offset: int,
        limit: int,
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        client_name: Optional[str],
        currency: Optional[str],
    ) -> tuple[int, list[CashEntry]]:
        """Return filtered paginated entries and total."""

        filters = [_not_deleted]
        if date_from is not None:
            filters.append(CashEntry.created_at >= date_from)
        if date_to is not None:
            filters.append(CashEntry.created_at <= date_to)
        if client_name:
            filters.append(func.lower(CashEntry.client_name) == client_name.strip().lower())
        if currency:
            filters.append(CashEntry.currency_code == currency.upper())

        total_query = select(func.count(CashEntry.id)).where(*filters)
        total_result = await session.execute(total_query)
        total = int(total_result.scalar_one())

        query = (
            select(CashEntry)
            .where(*filters)
            .order_by(CashEntry.created_at.desc(), CashEntry.id.desc())
            .offset(offset)
            .limit(limit)
        )

        rows = await session.execute(query)
        items = list(rows.scalars().all())
        return total, items

    async def daily_profit_by_currency(self, session: AsyncSession, target_date: date) -> dict[str, Decimal]:
        """Compute daily net flow by currency (inflow - outflow)."""

        start_dt, end_dt = _local_day_bounds(target_date)
        return await self._net_by_currency(session, start_dt=start_dt, end_dt=end_dt)

    async def currency_balances(self, session: AsyncSession) -> dict[str, Decimal]:
        """Compute all-time balances by currency (inflow - outflow)."""

        return await self._net_by_currency(session, start_dt=None, end_dt=None)

    async def client_debts(self, session: AsyncSession) -> list[tuple[str, str, Decimal, datetime]]:
        """Compute client debt per currency as outflow - inflow, including last update time."""

        debt_case = case(
            (CashEntry.flow_direction == "OUTFLOW", CashEntry.amount),
            else_=-CashEntry.amount,
        )

        query = (
            select(
                CashEntry.client_name,
                CashEntry.currency_code,
                func.coalesce(func.sum(debt_case), 0),
                func.max(CashEntry.created_at),
            )
            .where(_not_deleted)
            .group_by(CashEntry.client_name, CashEntry.currency_code)
            .order_by(CashEntry.client_name.asc(), CashEntry.currency_code.asc())
        )
        result = await session.execute(query)
        return [(r[0], r[1], r[2], r[3]) for r in result.all()]

    async def cash_total(self, session: AsyncSession) -> tuple[dict[str, Decimal], Decimal]:
        """Return by-currency balances and explicit UZS total."""

        by_currency = await self.currency_balances(session)
        uzs_total = by_currency.get("UZS", Decimal("0"))
        return by_currency, uzs_total

    async def entries_for_day(self, session: AsyncSession, target_date: date) -> list[CashEntry]:
        """Return all entries for a local day."""

        start_dt, end_dt = _local_day_bounds(target_date)
        result = await session.execute(
            select(CashEntry)
            .where(CashEntry.created_at >= start_dt, CashEntry.created_at <= end_dt, _not_deleted)
            .order_by(CashEntry.created_at.asc(), CashEntry.id.asc())
        )
        return list(result.scalars().all())

    async def _net_by_currency(
        self,
        session: AsyncSession,
        *,
        start_dt: Optional[datetime],
        end_dt: Optional[datetime],
    ) -> dict[str, Decimal]:
        """Reusable aggregation for inflow-outflow grouped by currency."""

        net_case = case(
            (CashEntry.flow_direction == "INFLOW", CashEntry.amount),
            else_=-CashEntry.amount,
        )

        query = select(
            CashEntry.currency_code,
            func.coalesce(func.sum(net_case), 0),
        ).where(_not_deleted).group_by(CashEntry.currency_code)

        if start_dt is not None:
            query = query.where(CashEntry.created_at >= start_dt)
        if end_dt is not None:
            query = query.where(CashEntry.created_at <= end_dt)

        result = await session.execute(query)
        return {code: amount for code, amount in result.all()}


def _local_day_bounds(target_date: date) -> tuple[datetime, datetime]:
    """Build timezone-aware day start/end using configured timezone."""

    settings = get_settings()
    tz = ZoneInfo(settings.timezone)
    return (
        datetime.combine(target_date, time.min, tzinfo=tz),
        datetime.combine(target_date, time.max, tzinfo=tz),
    )
