"""Async database engine/session management."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


class DatabaseManager:
    """Lifecycle manager for SQLAlchemy async engine."""

    def __init__(self) -> None:
        settings = get_settings()
        self._engine = create_async_engine(settings.database_url, echo=settings.debug, pool_pre_ping=True)
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def connect(self) -> None:
        """Warm connection lazily on startup (no-op placeholder)."""

        return None

    async def dispose(self) -> None:
        """Dispose engine cleanly on shutdown."""

        await self._engine.dispose()

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Expose the configured sessionmaker for use in services and bot."""

        return self._session_factory



db_manager = DatabaseManager()


async def get_db_session() -> AsyncSession:
    """FastAPI dependency that yields an async DB session."""

    async with db_manager.session_factory() as session:
        yield session
