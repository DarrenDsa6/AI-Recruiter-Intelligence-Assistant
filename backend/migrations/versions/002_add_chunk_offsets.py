"""add chunk offset columns

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
    op.add_column("resume_chunks", sa.Column("chunk_start_char", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("resume_chunks", sa.Column("chunk_end_char", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.alter_column("resume_chunks", "chunk_start_char", server_default=None)
    op.alter_column("resume_chunks", "chunk_end_char", server_default=None)


def downgrade() -> None:
    op.drop_column("resume_chunks", "chunk_end_char")
    op.drop_column("resume_chunks", "chunk_start_char")
