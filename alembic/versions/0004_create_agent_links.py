"""Create agent_links table for orchestration

Revision ID: 0004
Revises: 0003
Create Date: 2025-11-14

Changes:
- Create agent_links table for agent-to-agent routing
- Defines which agents can handoff to which other agents
- Includes trigger conditions and priority
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'agent_links',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('from_agent_id', sa.Integer(), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('to_agent_id', sa.Integer(), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('trigger_keywords', sa.Text(), nullable=True),  # JSON array de keywords
        sa.Column('priority', sa.Integer(), server_default='0', nullable=False),
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'))
    )
    
    # Índices para performance
    op.create_index('idx_agent_links_from', 'agent_links', ['from_agent_id'])
    op.create_index('idx_agent_links_to', 'agent_links', ['to_agent_id'])
    op.create_index('idx_agent_links_tenant', 'agent_links', ['tenant_id'])


def downgrade():
    op.drop_index('idx_agent_links_tenant', 'agent_links')
    op.drop_index('idx_agent_links_to', 'agent_links')
    op.drop_index('idx_agent_links_from', 'agent_links')
    op.drop_table('agent_links')

