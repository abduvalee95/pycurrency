"""Report endpoints for simplified cashflow model."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_backup_scheduler, get_entry_service, get_session
from app.schemas.report import (
    CashTotalReport,
    ClientDebtItem,
    ClientDebtReport,
    CurrencyBalancesReport,
    DailyProfitReport,
    ExportDailyCSVResponse,
)
from app.services.backup_service import BackupScheduler
from app.services.entry_service import EntryService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily-profit", response_model=DailyProfitReport)
async def daily_profit_report(
    target_date: date = Query(default_factory=date.today, alias="date"),
    session: AsyncSession = Depends(get_session),
    service: EntryService = Depends(get_entry_service),
) -> DailyProfitReport:
    """Return per-currency daily net flow."""

    data = await service.daily_profit_by_currency(session, target_date)
    return DailyProfitReport(date=target_date, by_currency=data)


@router.get("/currency-balances", response_model=CurrencyBalancesReport)
async def currency_balances_report(
    session: AsyncSession = Depends(get_session),
    service: EntryService = Depends(get_entry_service),
) -> CurrencyBalancesReport:
    """Return all-time balances by currency."""

    data = await service.currency_balances(session)
    return CurrencyBalancesReport(by_currency=data)


@router.get("/client-debts", response_model=ClientDebtReport)
async def client_debts_report(
    session: AsyncSession = Depends(get_session),
    service: EntryService = Depends(get_entry_service),
) -> ClientDebtReport:
    """Return client debt list by currency."""

    rows = await service.client_debts(session)
    items = [ClientDebtItem(client_name=client, currency_code=currency, debt_amount=debt) for client, currency, debt, _ in rows]
    return ClientDebtReport(items=items)


@router.get("/cash-total", response_model=CashTotalReport)
async def cash_total_report(
    session: AsyncSession = Depends(get_session),
    service: EntryService = Depends(get_entry_service),
) -> CashTotalReport:
    """Return cash total by currency and explicit UZS total."""

    by_currency, uzs_total = await service.cash_total(session)
    return CashTotalReport(by_currency=by_currency, uzs_total=uzs_total)


@router.post("/export-daily-csv", response_model=ExportDailyCSVResponse)
async def export_daily_csv(
    target_date: date = Query(default_factory=date.today, alias="date"),
    scheduler: BackupScheduler = Depends(get_backup_scheduler),
) -> ExportDailyCSVResponse:
    """Generate daily CSV backup and send files to admin Telegram."""

    result = await scheduler.run_once(target_date)
    return ExportDailyCSVResponse(
        date=target_date,
        entries_csv_path=str(result.entries_csv),
        reports_csv_path=str(result.reports_csv),
    )
