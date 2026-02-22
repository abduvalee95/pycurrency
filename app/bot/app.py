"""Telegram bot application entrypoint."""

from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers.main import router as main_router
from app.config import get_settings


async def run_bot() -> None:
    """Run polling bot process."""

    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(main_router)

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run_bot())
