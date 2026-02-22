"""Client schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseSchema


class ClientCreate(BaseModel):
    """Create payload for a client."""

    name: str = Field(min_length=1, max_length=128)
    phone: Optional[str] = Field(default=None, max_length=32)


class ClientRead(ORMBaseSchema):
    """Read model for clients."""

    id: int
    name: str
    phone: Optional[str]
    created_at: datetime
