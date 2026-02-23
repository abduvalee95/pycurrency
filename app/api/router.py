"""Top-level API router aggregation."""

from fastapi import APIRouter

from app.api.routes.ai import router as ai_router
from app.api.routes.balances import router as balances_router
from app.api.routes.clients import router as clients_router
from app.api.routes.entries import router as entries_router
from app.api.routes.reports import router as reports_router

api_router = APIRouter()
api_router.include_router(entries_router)
api_router.include_router(reports_router)
api_router.include_router(balances_router)
api_router.include_router(clients_router)
api_router.include_router(ai_router)
