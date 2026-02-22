from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.models import CashEntry
from app.schemas.entry import EntryCreate
from app.services.entry_service import EntryService


@pytest.mark.asyncio
async def test_report_aggregations_and_debt_formula(session_factory: async_sessionmaker[AsyncSession]) -> None:
    service = EntryService()

    async with session_factory() as session:
        await service.create_entry(
            session,
            EntryCreate(amount=Decimal("100"), currency_code="USD", flow_direction="INFLOW", client_name="Ali"),
            created_by_telegram_id=1001,
        )
        await service.create_entry(
            session,
            EntryCreate(amount=Decimal("30"), currency_code="USD", flow_direction="OUTFLOW", client_name="Ali"),
            created_by_telegram_id=1001,
        )
        await service.create_entry(
            session,
            EntryCreate(amount=Decimal("10"), currency_code="RUB", flow_direction="OUTFLOW", client_name="Ali"),
            created_by_telegram_id=1001,
        )
        await service.create_entry(
            session,
            EntryCreate(amount=Decimal("500"), currency_code="UZS", flow_direction="INFLOW", client_name="Bob"),
            created_by_telegram_id=1001,
        )
        await service.create_entry(
            session,
            EntryCreate(amount=Decimal("100"), currency_code="UZS", flow_direction="OUTFLOW", client_name="Bob"),
            created_by_telegram_id=1001,
        )

        today = date.today()
        daily_profit = await service.daily_profit_by_currency(session, today)
        balances = await service.currency_balances(session)
        debts = await service.client_debts(session)
        by_currency, uzs_total = await service.cash_total(session)

    assert daily_profit["USD"] == Decimal("70")
    assert daily_profit["RUB"] == Decimal("-10")
    assert daily_profit["UZS"] == Decimal("400")

    assert balances == daily_profit
    assert by_currency["UZS"] == Decimal("400")
    assert uzs_total == Decimal("400")

    debt_index = {(client, currency): amount for client, currency, amount in debts}
    assert debt_index[("Ali", "USD")] == Decimal("-70")  # outflow - inflow
    assert debt_index[("Ali", "RUB")] == Decimal("10")
    assert debt_index[("Bob", "UZS")] == Decimal("-400")


@pytest.mark.asyncio
async def test_daily_profit_respects_timezone_day_boundary(session_factory: async_sessionmaker[AsyncSession]) -> None:
    service = EntryService()
    tz = ZoneInfo("Asia/Bishkek")

    async with session_factory() as session:
        async with session.begin():
            session.add_all(
                [
                    CashEntry(
                        amount=Decimal("10"),
                        currency_code="USD",
                        flow_direction="INFLOW",
                        client_name="Boundary",
                        note=None,
                        created_by_telegram_id=1001,
                        created_at=datetime(2026, 2, 21, 23, 59, tzinfo=tz),
                    ),
                    CashEntry(
                        amount=Decimal("20"),
                        currency_code="USD",
                        flow_direction="INFLOW",
                        client_name="Boundary",
                        note=None,
                        created_by_telegram_id=1001,
                        created_at=datetime(2026, 2, 22, 0, 1, tzinfo=tz),
                    ),
                ]
            )

        d1 = await service.daily_profit_by_currency(session, date(2026, 2, 21))
        d2 = await service.daily_profit_by_currency(session, date(2026, 2, 22))

    assert d1["USD"] == Decimal("10")
    assert d2["USD"] == Decimal("20")
