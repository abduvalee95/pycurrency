"""Cash entry endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_entry_service, get_session
from app.schemas.entry import EntryCreate, EntryListResponse, EntryRead
from app.security.telegram_auth import get_request_telegram_id
from app.services.entry_service import EntryService

router = APIRouter(prefix="/entries", tags=["entries"])


@router.post("", response_model=EntryRead)
async def create_entry(
    payload: EntryCreate,
    session: AsyncSession = Depends(get_session),
    service: EntryService = Depends(get_entry_service),
    actor_telegram_id: int = Depends(get_request_telegram_id),
) -> EntryRead:
    """Create one cash entry."""

    entry = await service.create_entry(
        session=session,
        payload=payload,
        created_by_telegram_id=actor_telegram_id,
    )
    return EntryRead.model_validate(entry)


@router.get("", response_model=EntryListResponse)
async def list_entries(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    client_name: Optional[str] = Query(default=None),
    currency: Optional[str] = Query(default=None, min_length=3, max_length=3),
    session: AsyncSession = Depends(get_session),
    service: EntryService = Depends(get_entry_service),
) -> EntryListResponse:
    """List entries with optional filters."""

    total, items = await service.list_entries(
        session=session,
        offset=offset,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        client_name=client_name,
        currency=currency,
    )
    return EntryListResponse(total=total, items=[EntryRead.model_validate(row) for row in items])
