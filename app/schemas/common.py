"""Common schema helpers."""

from datetime import datetime

from pydantic import BaseModel


class ORMBaseSchema(BaseModel):
    """Base schema with ORM compatibility enabled."""

    model_config = {"from_attributes": True}


class TimeRange(BaseModel):
    """Reusable time-range payload."""

    start_at: datetime
    end_at: datetime
