"""Add role and is_approved to users

Revision ID: 0008_add_role_approval
Revises: 0007_add_status_to_users
Create Date: 2025-11-18 12:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0008_add_role_approval"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar coluna role (OWNER, ADMIN, USER)
    op.add_column("users", sa.Column("role", sa.Text, server_default="USER", nullable=False))
    
    # Adicionar coluna is_approved (boolean)
    op.add_column("users", sa.Column("is_approved", sa.Boolean, server_default="false", nullable=False))
    
    # Atualizar usuário owner existente (se houver)
    op.execute("""
        UPDATE users 
        SET role = 'OWNER', is_approved = true 
        WHERE email = 'dangraebin@gmail.com'
    """)


def downgrade():
    op.drop_column("users", "is_approved")
    op.drop_column("users", "role")

