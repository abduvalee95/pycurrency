"""Currency schemas."""

from app.schemas.common import ORMBaseSchema


class CurrencyRead(ORMBaseSchema):
    """Read model for currency."""

    id: int
    code: str
    name: str
