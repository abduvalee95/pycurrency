"""Helpers to run Alembic migrations programmatically."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import get_settings


def _alembic_config() -> Config:
    """Load Alembic configuration and inject runtime DB URL."""

    settings = get_settings()
    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def should_run_migrations() -> bool:
    """Run automatically on Render or when explicitly enabled."""

    render_flag = os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID")
    # Avoid concurrent runs from multiple services; prefer the web service.
    service_name = os.getenv("RENDER_SERVICE_NAME")
    if render_flag and service_name and "pycurrency" not in service_name:
        render_flag = False

    manual_flag = os.getenv("RUN_MIGRATIONS_ON_STARTUP", "false").lower() == "true"
    return bool(render_flag or manual_flag)


async def run_migrations() -> None:
    """Apply latest Alembic migrations."""

    cfg = _alembic_config()
    # Alembic is synchronous; offload to a worker thread to avoid blocking the event loop.
    await asyncio.to_thread(command.upgrade, cfg, "head")
