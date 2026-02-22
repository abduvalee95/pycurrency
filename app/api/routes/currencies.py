"""Currency endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.currency import CurrencyRead
from app.services.currency_service import CurrencyService

router = APIRouter(prefix="/currencies", tags=["currencies"])
service = CurrencyService()


@router.get("", response_model=list[CurrencyRead])
async def list_currencies(session: AsyncSession = Depends(get_session)) -> list[CurrencyRead]:
    """List all configured currencies."""

    rows = await service.list_currencies(session)
    return [CurrencyRead.model_validate(row) for row in rows]
