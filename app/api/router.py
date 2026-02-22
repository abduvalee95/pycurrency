"""Top-level API router aggregation."""

from fastapi import APIRouter

from app.api.routes.ai import router as ai_router
from app.api.routes.entries import router as entries_router
from app.api.routes.reports import router as reports_router

api_router = APIRouter()
api_router.include_router(entries_router)
api_router.include_router(reports_router)
api_router.include_router(ai_router)
