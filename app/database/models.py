
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy import event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class TransactionType(str, Enum):
    """Type of transaction."""
    
    BUY = "BUY"
    SELL = "SELL"


class FlowDirection(str, Enum):
    """Simple cashflow direction for entries."""

    INFLOW = "INFLOW"
    OUTFLOW = "OUTFLOW"


class Currency(Base):
    """Supported currency for transactions and ledger entries."""

    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(3), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)


class Client(Base):
    """Exchange customer profile."""

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transactions: Mapped[list[Transaction]] = relationship(back_populates="client")


class Transaction(Base):
    """Exchange operation (outgoing currency and incoming currency)."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), index=True)
    to_currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), index=True)
    from_amount: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    to_amount: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    rate: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    client_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clients.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    from_currency: Mapped[Currency] = relationship(foreign_keys=[from_currency_id])
    to_currency: Mapped[Currency] = relationship(foreign_keys=[to_currency_id])
    client: Mapped[Optional[Client]] = relationship(back_populates="transactions")
    ledger_entries: Mapped[list[LedgerEntry]] = relationship(back_populates="transaction")


class LedgerEntry(Base):
    """Immutable accounting movement record for a single currency."""

    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    currency: Mapped[Currency] = relationship()
    transaction: Mapped[Transaction] = relationship(back_populates="ledger_entries")


class CashEntry(Base):
    """Simplified cashflow entry model."""

    __tablename__ = "cash_entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_cash_entries_amount_positive"),
        CheckConstraint(
            "currency_code IN ('USD', 'RUB', 'UZS')",
            name="ck_cash_entries_currency_code_allowed",
        ),
        CheckConstraint(
            "flow_direction IN ('INFLOW', 'OUTFLOW')",
            name="ck_cash_entries_flow_direction_allowed",
        ),
        Index("ix_cash_entries_currency_created", "currency_code", "created_at"),
        Index("ix_cash_entries_client_currency_created", "client_name", "currency_code", "created_at"),
        Index("ix_cash_entries_created_by_created", "created_by_telegram_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    currency_code: Mapped[str] = mapped_column(String(3), index=True)
    flow_direction: Mapped[str] = mapped_column(String(8), index=True)
    client_name: Mapped[str] = mapped_column(String(128), index=True)
    note: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_by_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None, index=True)


@event.listens_for(LedgerEntry, "before_update", propagate=True)
def _prevent_ledger_update(*_args, **_kwargs):
    """Guarantee immutability of ledger entries once persisted."""

    raise ValueError("Ledger entries are immutable and cannot be updated")


@event.listens_for(LedgerEntry, "before_delete", propagate=True)
def _prevent_ledger_delete(*_args, **_kwargs):
    """Guarantee immutability of ledger entries once persisted."""

    raise ValueError("Ledger entries are immutable and cannot be deleted")
