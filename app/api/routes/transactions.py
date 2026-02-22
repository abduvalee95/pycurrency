"""Transaction endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.accounting.engine import AccountingEngine
from app.api.deps import get_accounting_engine, get_session
from app.database.models import Transaction
from app.schemas.transaction import (
    AIOperatorConfirmRequest,
    TransactionCreate,
    TransactionHistoryResponse,
    TransactionRead,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionRead)
async def create_transaction(
    payload: TransactionCreate,
    session: AsyncSession = Depends(get_session),
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> TransactionRead:
    """Create exchange transaction via manual payload."""

    tx = await engine.create_manual_transaction(session=session, payload=payload)
    return TransactionRead.model_validate(tx)


@router.post("/ai-confirm", response_model=TransactionRead)
async def create_transaction_from_ai(
    payload: AIOperatorConfirmRequest,
    session: AsyncSession = Depends(get_session),
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> TransactionRead:
    """Create transaction from operator-confirmed AI parse result."""

    tx = await engine.create_from_ai_confirmation(session=session, payload=payload)
    return TransactionRead.model_validate(tx)


@router.get("", response_model=TransactionHistoryResponse)
async def transaction_history(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> TransactionHistoryResponse:
    """Paginated transaction history newest first."""

    total_result = await session.execute(select(func.count(Transaction.id)))
    total = int(total_result.scalar_one())

    result = await session.execute(
        select(Transaction)
        .options(
            joinedload(Transaction.from_currency),
            joinedload(Transaction.to_currency),
            joinedload(Transaction.client),
        )
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items = list(result.scalars().all())

    return TransactionHistoryResponse(
        total=total,
        items=[TransactionRead.model_validate(item) for item in items],
    )
