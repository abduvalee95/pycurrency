"""Initial schema for exchange accounting MVP.

Revision ID: 0001_initial
Revises:
Create Date: 2026-02-13 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "currencies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_currencies")),
        sa.UniqueConstraint("code", name=op.f("uq_currencies_code")),
        sa.UniqueConstraint("name", name=op.f("uq_currencies_name")),
    )
    op.create_index(op.f("ix_currencies_code"), "currencies", ["code"], unique=False)

    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clients")),
    )
    op.create_index(op.f("ix_clients_name"), "clients", ["name"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("from_currency_id", sa.Integer(), nullable=False),
        sa.Column("to_currency_id", sa.Integer(), nullable=False),
        sa.Column("from_amount", sa.Numeric(24, 8), nullable=False),
        sa.Column("to_amount", sa.Numeric(24, 8), nullable=False),
        sa.Column("rate", sa.Numeric(24, 8), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name=op.f("fk_transactions_client_id_clients")),
        sa.ForeignKeyConstraint(
            ["from_currency_id"],
            ["currencies.id"],
            name=op.f("fk_transactions_from_currency_id_currencies"),
        ),
        sa.ForeignKeyConstraint(
            ["to_currency_id"],
            ["currencies.id"],
            name=op.f("fk_transactions_to_currency_id_currencies"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactions")),
    )
    op.create_index(op.f("ix_transactions_client_id"), "transactions", ["client_id"], unique=False)
    op.create_index(op.f("ix_transactions_created_at"), "transactions", ["created_at"], unique=False)
    op.create_index(op.f("ix_transactions_from_currency_id"), "transactions", ["from_currency_id"], unique=False)
    op.create_index(op.f("ix_transactions_to_currency_id"), "transactions", ["to_currency_id"], unique=False)

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("currency_id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(24, 8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currencies.id"],
            name=op.f("fk_ledger_entries_currency_id_currencies"),
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name=op.f("fk_ledger_entries_transaction_id_transactions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_entries")),
    )
    op.create_index(op.f("ix_ledger_entries_created_at"), "ledger_entries", ["created_at"], unique=False)
    op.create_index(op.f("ix_ledger_entries_currency_id"), "ledger_entries", ["currency_id"], unique=False)
    op.create_index(op.f("ix_ledger_entries_transaction_id"), "ledger_entries", ["transaction_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ledger_entries_transaction_id"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_currency_id"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_created_at"), table_name="ledger_entries")
    op.drop_table("ledger_entries")

    op.drop_index(op.f("ix_transactions_to_currency_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_from_currency_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_created_at"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_client_id"), table_name="transactions")
    op.drop_table("transactions")

    op.drop_index(op.f("ix_clients_name"), table_name="clients")
    op.drop_table("clients")

    op.drop_index(op.f("ix_currencies_code"), table_name="currencies")
    op.drop_table("currencies")
