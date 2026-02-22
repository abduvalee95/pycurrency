"""Add cash_entries table for simplified cashflow model.

Revision ID: 0002_cash_entries
Revises: 0001_initial
Create Date: 2026-02-21 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_cash_entries"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cash_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(24, 8), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("flow_direction", sa.String(length=8), nullable=False),
        sa.Column("client_name", sa.String(length=128), nullable=False),
        sa.Column("note", sa.String(length=512), nullable=True),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cash_entries")),
    )

    op.create_index(op.f("ix_cash_entries_created_at"), "cash_entries", ["created_at"], unique=False)
    op.create_index(op.f("ix_cash_entries_currency_code"), "cash_entries", ["currency_code"], unique=False)
    op.create_index(op.f("ix_cash_entries_flow_direction"), "cash_entries", ["flow_direction"], unique=False)
    op.create_index(op.f("ix_cash_entries_client_name"), "cash_entries", ["client_name"], unique=False)
    op.create_index(
        "ix_cash_entries_currency_created",
        "cash_entries",
        ["currency_code", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_cash_entries_client_currency_created",
        "cash_entries",
        ["client_name", "currency_code", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_cash_entries_created_by_created",
        "cash_entries",
        ["created_by_telegram_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cash_entries_created_by_created", table_name="cash_entries")
    op.drop_index("ix_cash_entries_client_currency_created", table_name="cash_entries")
    op.drop_index("ix_cash_entries_currency_created", table_name="cash_entries")
    op.drop_index(op.f("ix_cash_entries_client_name"), table_name="cash_entries")
    op.drop_index(op.f("ix_cash_entries_flow_direction"), table_name="cash_entries")
    op.drop_index(op.f("ix_cash_entries_currency_code"), table_name="cash_entries")
    op.drop_index(op.f("ix_cash_entries_created_at"), table_name="cash_entries")
    op.drop_table("cash_entries")
