"""Add status to users

Revision ID: 0007
Revises: 0006
Create Date: 2025-11-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    # Add status column to users table
    op.add_column('users', sa.Column('status', sa.Text(), server_default='PENDING', nullable=False))
    
    # Atualizar usuários existentes para APPROVED
    op.execute("UPDATE users SET status = 'APPROVED' WHERE status = 'PENDING'")


def downgrade():
    # Remove status column from users table
    op.drop_column('users', 'status')

