"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector extension (run separately if this fails inside transaction)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text(), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "master_resumes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_hash", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "file_hash", name="uq_user_file_hash"),
    )
    op.create_index("ix_master_resumes_user_id", "master_resumes", ["user_id"])

    op.create_table(
        "resume_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("resume_id", UUID(as_uuid=True), sa.ForeignKey("master_resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("skills", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_resume_chunks_resume_id", "resume_chunks", ["resume_id"])
    op.create_index("ix_resume_chunks_resume_id_chunk", "resume_chunks", ["resume_id", "chunk_index"])

    op.create_table(
        "tailoring_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", UUID(as_uuid=True), sa.ForeignKey("master_resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("jd_text", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending"),
        sa.Column("match_result", JSONB, nullable=True),
        sa.Column("github_analysis", JSONB, nullable=True),
        sa.Column("report", JSONB, nullable=True),
        sa.Column("questions", JSONB, nullable=True),
        sa.Column("rewrites", JSONB, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tailoring_reports_user_id", "tailoring_reports", ["user_id"])
    op.create_index("ix_tailoring_reports_resume_id", "tailoring_reports", ["resume_id"])

    # Row Level Security
    for table in ["users", "master_resumes", "resume_chunks", "tailoring_reports"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    op.execute('CREATE POLICY "Users can view own profile" ON users FOR SELECT USING (id = auth.uid())')
    op.execute('CREATE POLICY "Users can update own profile" ON users FOR UPDATE USING (id = auth.uid())')

    op.execute('CREATE POLICY "Users can view own resumes" ON master_resumes FOR SELECT USING (user_id = auth.uid())')
    op.execute('CREATE POLICY "Users can insert own resumes" ON master_resumes FOR INSERT WITH CHECK (user_id = auth.uid())')
    op.execute('CREATE POLICY "Users can update own resumes" ON master_resumes FOR UPDATE USING (user_id = auth.uid())')
    op.execute('CREATE POLICY "Users can delete own resumes" ON master_resumes FOR DELETE USING (user_id = auth.uid())')

    op.execute('''CREATE POLICY "Users can view own chunks" ON resume_chunks FOR SELECT USING (
        EXISTS (SELECT 1 FROM master_resumes WHERE master_resumes.id = resume_chunks.resume_id AND master_resumes.user_id = auth.uid())
    )''')
    op.execute('''CREATE POLICY "Users can insert own chunks" ON resume_chunks FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM master_resumes WHERE master_resumes.id = resume_chunks.resume_id AND master_resumes.user_id = auth.uid())
    )''')
    op.execute('''CREATE POLICY "Users can delete own chunks" ON resume_chunks FOR DELETE USING (
        EXISTS (SELECT 1 FROM master_resumes WHERE master_resumes.id = resume_chunks.resume_id AND master_resumes.user_id = auth.uid())
    )''')

    op.execute('CREATE POLICY "Users can view own reports" ON tailoring_reports FOR SELECT USING (user_id = auth.uid())')
    op.execute('CREATE POLICY "Users can insert own reports" ON tailoring_reports FOR INSERT WITH CHECK (user_id = auth.uid())')
    op.execute('CREATE POLICY "Users can update own reports" ON tailoring_reports FOR UPDATE USING (user_id = auth.uid())')
    op.execute('CREATE POLICY "Users can delete own reports" ON tailoring_reports FOR DELETE USING (user_id = auth.uid())')


def downgrade() -> None:
    op.drop_table("tailoring_reports")
    op.drop_table("resume_chunks")
    op.drop_table("master_resumes")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
