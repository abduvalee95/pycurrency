"""Seed standard currencies for the exchange platform."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.database.models import Currency
from app.database.session import db_manager


CURRENCIES = [
    ("USD", "US Dollar"),
    ("RUB", "Russian Ruble"),
    ("UZS", "Uzbekistan Sum"),
    ("KGS", "Kyrgyzstan Som"),
    ("EUR", "Euro"),
]


async def seed() -> None:
    """Insert currencies if they do not already exist."""

    async with db_manager.session_factory() as session:
        async with session.begin():
            for code, name in CURRENCIES:
                existing = await session.execute(select(Currency).where(Currency.code == code).limit(1))
                if existing.scalar_one_or_none() is None:
                    session.add(Currency(code=code, name=name))

    print("Currency seed completed")


if __name__ == "__main__":
    asyncio.run(seed())
