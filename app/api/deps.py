"""Dependency helpers for API layer."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.parser import AIParserService
from app.config import Settings, get_settings
from app.database.session import db_manager, get_db_session
from app.services.backup_service import BackupScheduler
from app.services.entry_service import EntryService


async def get_session(session: AsyncSession = Depends(get_db_session)) -> AsyncSession:
    """Pass through DB session dependency for explicit typing."""

    return session


def get_entry_service() -> EntryService:
    """Build cash entry service dependency."""

    return EntryService()


def get_backup_scheduler(settings: Settings = Depends(get_settings)) -> BackupScheduler:
    """Build backup scheduler dependency."""

    return BackupScheduler(db_manager.session_factory, settings)


def get_ai_parser(settings: Settings = Depends(get_settings)) -> AIParserService:
    """Build AI parser service dependency."""

    return AIParserService.from_settings(settings)
