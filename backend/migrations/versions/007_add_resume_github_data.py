"""add github_data JSONB column to master_resumes

GitHub repo data previously lived only as resume_chunks (section='github'),
which polluted resume matching, rewrites, and RAG retrieval with README text.
This revision adds a resume-level JSONB column so repo/readme data is stored
separately and only used for the GitHub Insights section.

Revision ID: 007
Revises: 006
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "007"
down_revision: Union[str, None] = "006"
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
    if not _column_exists("master_resumes", "github_data"):
        op.add_column("master_resumes", sa.Column("github_data", JSONB, nullable=True))


def downgrade() -> None:
    if _column_exists("master_resumes", "github_data"):
        op.drop_column("master_resumes", "github_data")
