"""Add provider to agents

Revision ID: 0006
Revises: 0005
Create Date: 2025-11-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    # Add provider column to agents table
    op.add_column('agents', sa.Column('provider', sa.Text(), server_default='openai', nullable=False))


def downgrade():
    # Remove provider column from agents table
    op.drop_column('agents', 'provider')

