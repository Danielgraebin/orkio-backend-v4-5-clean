"""Update rag_events schema for v4

Revision ID: 0003
Revises: 0002
Create Date: 2025-11-14

Changes:
- Add message_id column
- Replace top_k and used_chunks with chunks_retrieved and chunks_used
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old columns
    op.drop_column('rag_events', 'top_k')
    op.drop_column('rag_events', 'used_chunks')
    
    # Add new columns
    op.add_column('rag_events', sa.Column('message_id', sa.Integer(), sa.ForeignKey('conversation_messages.id'), nullable=True))
    op.add_column('rag_events', sa.Column('chunks_retrieved', sa.Integer(), server_default='0', nullable=False))
    op.add_column('rag_events', sa.Column('chunks_used', sa.Integer(), server_default='0', nullable=False))


def downgrade():
    # Revert changes
    op.drop_column('rag_events', 'chunks_used')
    op.drop_column('rag_events', 'chunks_retrieved')
    op.drop_column('rag_events', 'message_id')
    
    op.add_column('rag_events', sa.Column('top_k', sa.Integer(), nullable=True))
    op.add_column('rag_events', sa.Column('used_chunks', sa.JSON(), nullable=True))

