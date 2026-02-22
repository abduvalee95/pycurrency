"""Balance endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_balance_service, get_session
from app.ledger.service import LedgerService
from app.schemas.balance import BalanceResponse
from app.services.balance_service import BalanceService

router = APIRouter(prefix="/balances", tags=["balances"])


@router.get("", response_model=BalanceResponse)
async def list_balances(
    session: AsyncSession = Depends(get_session),
    service: BalanceService = Depends(get_balance_service),
) -> BalanceResponse:
    """Return balances grouped by currency."""

    return await service.get_all_balances(session)


@router.get("/{currency_code}", response_model=Decimal)
async def get_currency_balance(
    currency_code: str,
    session: AsyncSession = Depends(get_session),
) -> Decimal:
    """Return current balance for one currency."""

    ledger = LedgerService()
    return await ledger.balance_for_currency(session=session, currency_code=currency_code)
