"""add chat_messages table for persistent chat history

Chat history previously lived only in Redis with a 1-hour TTL and was lost
for previous reports. This revision adds a durable Postgres table keyed by
resume_id (preserving the existing per-resume conversation semantics).

Revision ID: 006
Revises: 005
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :table"),
        {"table": table},
    )
    return result.scalar() is not None


def upgrade() -> None:
    if _table_exists("chat_messages"):
        return

    op.create_table(
        "chat_messages",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("tailoring_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resume_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_chat_messages_resume_id", "chat_messages", ["resume_id"])
    op.create_index("ix_chat_messages_report_id", "chat_messages", ["report_id"])
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])


def downgrade() -> None:
    if _table_exists("chat_messages"):
        op.drop_table("chat_messages")
