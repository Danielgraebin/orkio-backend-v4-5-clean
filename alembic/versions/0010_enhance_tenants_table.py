"""enhance tenants table

Revision ID: 0010
Revises: 0009
Create Date: 2025-11-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to tenants table
    op.add_column('tenants', sa.Column('slug', sa.String(100), nullable=True, unique=True))
    op.add_column('tenants', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('tenants', sa.Column('updated_at', sa.DateTime(), server_default=func.now(), onupdate=func.now()))
    op.add_column('tenants', sa.Column('default_provider', sa.String(50), nullable=True))
    op.add_column('tenants', sa.Column('allowed_models', sa.JSON(), nullable=True))
    
    # Generate slugs for existing tenants (lowercase name with hyphens)
    op.execute("""
        UPDATE tenants 
        SET slug = LOWER(REPLACE(name, ' ', '-'))
        WHERE slug IS NULL
    """)
    
    # Make slug non-nullable after populating
    op.alter_column('tenants', 'slug', nullable=False)


def downgrade():
    op.drop_column('tenants', 'allowed_models')
    op.drop_column('tenants', 'default_provider')
    op.drop_column('tenants', 'updated_at')
    op.drop_column('tenants', 'is_active')
    op.drop_column('tenants', 'slug')
