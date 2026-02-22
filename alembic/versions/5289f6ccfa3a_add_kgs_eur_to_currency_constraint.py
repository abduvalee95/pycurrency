"""add_kgs_eur_to_currency_constraint

Revision ID: 5289f6ccfa3a
Revises: bf5111584636
Create Date: 2026-02-22 13:28:25.900336
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5289f6ccfa3a'
down_revision = 'bf5111584636'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old constraint and add new one with KGS and EUR
    op.drop_constraint('ck_cash_entries_currency_code_allowed', 'cash_entries', type_='check')
    op.create_check_constraint(
        'ck_cash_entries_currency_code_allowed',
        'cash_entries',
        "currency_code IN ('USD', 'RUB', 'UZS', 'KGS', 'EUR')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_cash_entries_currency_code_allowed', 'cash_entries', type_='check')
    op.create_check_constraint(
        'ck_cash_entries_currency_code_allowed',
        'cash_entries',
        "currency_code IN ('USD', 'RUB', 'UZS')",
    )
