from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_session
from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.config import get_settings
from app.database.base import Base
from app.security.telegram_auth import require_api_auth


@pytest.fixture(autouse=True)
def _settings_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Set deterministic test env and reset cached Settings."""

    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "1001,1002")
    monkeypatch.setenv("TELEGRAM_WEBAPP_ENFORCE", "false")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("TIMEZONE", "Asia/Bishkek")
    monkeypatch.setenv("BACKUPS_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-bot-token")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def session_factory(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    """Provide isolated sqlite session factory per test."""

    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest.fixture
def api_app(session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    """Build API app with test DB dependency override."""

    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1", dependencies=[Depends(require_api_auth)])
    register_exception_handlers(app)

    async def override_get_session() -> AsyncSession:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    return app


@pytest_asyncio.fixture
async def api_client(api_app: FastAPI) -> httpx.AsyncClient:
    """ASGI client for API integration tests."""

    transport = httpx.ASGITransport(app=api_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def allowed_headers() -> dict[str, str]:
    return {"X-Telegram-Id": "1001"}


@pytest.fixture
def denied_headers() -> dict[str, str]:
    return {"X-Telegram-Id": "9999"}
