"""idempotently backfill resume_chunks.section and report agent columns

Databases bootstrapped from the standalone 001_initial_schema.sql predate
migration 003 (section / agent_analysis / interview_prep / outreach_email)
and migration 004 (pgvector index). If alembic is already stamped at 004,
upgrade head is a no-op and the app fails at runtime. This revision
guards every DDL with an information_schema check so it is safe to apply
regardless of the actual schema state.

Revision ID: 005
Revises: 004
Create Date: 2026-07-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.scalar() is not None


def upgrade() -> None:
    if not _column_exists("resume_chunks", "section"):
        op.add_column("resume_chunks", sa.Column("section", sa.Text(), nullable=True))

    for column in ("agent_analysis", "interview_prep", "outreach_email"):
        if not _column_exists("tailoring_reports", column):
            op.add_column("tailoring_reports", sa.Column(column, JSONB, nullable=True))

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_resume_chunks_embedding "
        "ON resume_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    if _column_exists("resume_chunks", "section"):
        op.drop_column("resume_chunks", "section")

    for column in ("agent_analysis", "interview_prep", "outreach_email"):
        if _column_exists("tailoring_reports", column):
            op.drop_column("tailoring_reports", column)
