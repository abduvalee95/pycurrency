"""Client endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_service, get_session
from app.schemas.client import ClientCreate, ClientRead
from app.services.client_service import ClientService

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
async def list_clients(
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    service: ClientService = Depends(get_client_service),
) -> list[ClientRead]:
    """List latest clients."""

    rows = await service.list_clients(session=session, limit=limit)
    return [ClientRead.model_validate(row) for row in rows]


@router.post("", response_model=ClientRead)
async def create_client(
    payload: ClientCreate,
    session: AsyncSession = Depends(get_session),
    service: ClientService = Depends(get_client_service),
) -> ClientRead:
    """Create a new client profile."""

    async with session.begin():
        client = await service.create_client(session=session, name=payload.name, phone=payload.phone)
    return ClientRead.model_validate(client)
