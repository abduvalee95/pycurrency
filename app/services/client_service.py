"""Client CRUD/use-case service."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Client


class ClientService:
    """Service for creating and resolving clients."""

    async def list_clients(self, session: AsyncSession, limit: int = 100) -> list[Client]:
        """Return newest clients first."""

        result = await session.execute(select(Client).order_by(Client.created_at.desc()).limit(limit))
        return list(result.scalars().all())

    async def create_client(self, session: AsyncSession, name: str, phone: Optional[str] = None) -> Client:
        """Create and persist a new client."""

        client = Client(name=name.strip(), phone=phone)
        session.add(client)
        await session.flush()
        await session.refresh(client)
        return client

    async def get_or_create_by_name(self, session: AsyncSession, name: str) -> Client:
        """Find client by normalized name or create a new row."""

        normalized = name.strip()
        result = await session.execute(select(Client).where(Client.name == normalized).limit(1))
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        return await self.create_client(session=session, name=normalized)
