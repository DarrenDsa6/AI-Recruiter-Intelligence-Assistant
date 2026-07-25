"""remove offset columns (text stored directly in chunk)

Revision ID: 002
Revises: 001
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
