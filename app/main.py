"""FastAPI dasturining kirish nuqtasi (entrypoint)."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.config import get_settings
from app.database.session import db_manager
from app.security.telegram_auth import require_api_auth
from app.services.backup_service import BackupScheduler
from app.web.router import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ulashilgan resurslar (ma'lumotlar bazasi, zaxiralash) uchun ishga tushish 
    va to'xtash (startup/shutdown) jarayonlarini boshqarish.
    """

    settings = get_settings()
    backup_scheduler = BackupScheduler(db_manager.session_factory, settings)
    backup_scheduler.start()

    await db_manager.connect()
    try:
        yield
    finally:
        await backup_scheduler.stop()
        await db_manager.dispose()


settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.include_router(api_router, prefix=settings.api_v1_prefix, dependencies=[Depends(require_api_auth)])
app.include_router(web_router)
register_exception_handlers(app)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Dastur ishlash holatini tekshirish (uptime checks) uchun oddiy endpoint."""

    return {"status": "ok"}
