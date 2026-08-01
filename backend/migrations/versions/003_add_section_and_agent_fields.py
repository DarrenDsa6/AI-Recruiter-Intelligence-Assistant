"""add section to chunks, agent_analysis/interview_prep/outreach_email to reports

Revision ID: 003
Revises: 002
Create Date: 2026-07-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("resume_chunks", sa.Column("section", sa.Text(), nullable=True))

    op.add_column("tailoring_reports", sa.Column("agent_analysis", JSONB, nullable=True))
    op.add_column("tailoring_reports", sa.Column("interview_prep", JSONB, nullable=True))
    op.add_column("tailoring_reports", sa.Column("outreach_email", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("resume_chunks", "section")

    op.drop_column("tailoring_reports", "agent_analysis")
    op.drop_column("tailoring_reports", "interview_prep")
    op.drop_column("tailoring_reports", "outreach_email")
