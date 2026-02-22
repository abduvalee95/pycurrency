from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.session import db_manager
from app.services.entry_service import EntryService
from app.schemas.entry import EntryRead
from app.web.auth import validate_telegram_data

router = APIRouter()

async def get_db_session():
    """Dependency to get DB session."""
    async with db_manager.session_factory() as session:
        yield session

def verify_init_data(x_tg_init_data: str = Header(None, alias="X-TG-Init-Data")):
    """Dependency to verify Telegram Mini App initData."""
    if not get_settings().debug:
        if not x_tg_init_data or not validate_telegram_data(x_tg_init_data):
            raise HTTPException(status_code=401, detail="Invalid Telegram Init Data")
    return x_tg_init_data


@router.get("/reports", dependencies=[Depends(verify_init_data)])
async def get_dashboard_reports(session: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    """Get aggregated data for the dashboard."""
    settings = get_settings()
    service = EntryService()
    today = datetime.now(ZoneInfo(settings.timezone)).date()

    # Get data
    balances = await service.currency_balances(session)
    daily_profits = await service.daily_profit_by_currency(session, today)
    debts = await service.client_debts(session)
    
    # Get last 20 entries
    _, entries = await service.list_entries(
        session=session,
        offset=0,
        limit=20,
        date_from=None,
        date_to=None,
        client_name=None,
        currency=None,
    )
    
    return {
        "balances": balances,
        "daily_profits": daily_profits,
        "debts": [{"client": c, "currency": cur, "amount": float(a)} for c, cur, a in debts],
        "recent_entries": [
            {
                "id": e.id,
                "amount": float(e.amount),
                "currency_code": e.currency_code,
                "flow_direction": e.flow_direction,
                "client_name": e.client_name,
                "note": e.note,
                "created_at": e.created_at.isoformat()
            }
            for e in entries
        ],
    }
