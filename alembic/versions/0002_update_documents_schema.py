"""Update documents schema for v4 RAG

Revision ID: 0002
Revises: 0001
Create Date: 2025-11-14

Changes:
- Remove 'content' column (text stored in chunks now)
- Add 'storage_path' column (file location)
- Add 'size_bytes' column (file size)
- Add 'status' column (PENDING/PROCESSING/READY/ERROR)
- Add 'tags' column (optional metadata)
- Update knowledge_chunks: rename 'chunk' to 'content', add 'chunk_index'
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # === UPDATE DOCUMENTS TABLE ===
    
    # Drop old 'content' column
    op.drop_column('documents', 'content')
    
    # Add new columns
    op.add_column('documents', sa.Column('storage_path', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('size_bytes', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('status', sa.Text(), server_default='PENDING', nullable=False))
    op.add_column('documents', sa.Column('tags', sa.Text(), nullable=True))
    
    # === UPDATE KNOWLEDGE_CHUNKS TABLE ===
    
    # Rename 'chunk' to 'content'
    op.alter_column('knowledge_chunks', 'chunk', new_column_name='content')
    
    # Add chunk_index
    op.add_column('knowledge_chunks', sa.Column('chunk_index', sa.Integer(), server_default='0', nullable=False))


def downgrade():
    # Revert knowledge_chunks
    op.drop_column('knowledge_chunks', 'chunk_index')
    op.alter_column('knowledge_chunks', 'content', new_column_name='chunk')
    
    # Revert documents
    op.drop_column('documents', 'tags')
    op.drop_column('documents', 'status')
    op.drop_column('documents', 'size_bytes')
    op.drop_column('documents', 'storage_path')
    op.add_column('documents', sa.Column('content', sa.Text(), nullable=False))

