"""Add validation constraints for cash_entries model.

Revision ID: 0003_cash_entries_constraints
Revises: 0002_cash_entries
Create Date: 2026-02-22 00:00:00
"""

from alembic import op


revision = "0003_cash_entries_constraints"
down_revision = "0002_cash_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_cash_entries_amount_positive",
        "cash_entries",
        "amount > 0",
    )
    op.create_check_constraint(
        "ck_cash_entries_currency_code_allowed",
        "cash_entries",
        "currency_code IN ('USD', 'RUB', 'UZS')",
    )
    op.create_check_constraint(
        "ck_cash_entries_flow_direction_allowed",
        "cash_entries",
        "flow_direction IN ('INFLOW', 'OUTFLOW')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_cash_entries_flow_direction_allowed", "cash_entries", type_="check")
    op.drop_constraint("ck_cash_entries_currency_code_allowed", "cash_entries", type_="check")
    op.drop_constraint("ck_cash_entries_amount_positive", "cash_entries", type_="check")
