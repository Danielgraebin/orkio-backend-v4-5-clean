"""Add model field to agents

Revision ID: 0005
Revises: 0004
Create Date: 2025-11-14

Changes:
- Add model column to agents table (default: gpt-4.1-mini)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    # Add model column
    op.add_column('agents', sa.Column('model', sa.Text(), server_default='gpt-4.1-mini', nullable=False))


def downgrade():
    # Remove model column
    op.drop_column('agents', 'model')

