"""add pgvector ivfflat index"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None

def upgrade():
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_resume_chunks_embedding "
        "ON resume_chunks USING hnsw (embedding vector_cosine_ops)"
    )

def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_resume_chunks_embedding")
