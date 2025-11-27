"""Multi-LLM providers and API keys management

Revision ID: 0009
Revises: 0008
Create Date: 2025-11-18 13:40:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '0009_multi_llm'
down_revision = '0008_add_role_approval'
branch_labels = None
depends_on = None

def upgrade():
    # Tabela de providers (OpenAI, Gemini, Anthropic, Mistral, Llama, Local)
    op.create_table(
        'llm_providers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('slug', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    
    # Tabela de modelos por provider
    op.create_table(
        'llm_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),  # Nome amigável (ex: "GPT-4.1 Mini")
        sa.Column('model_id', sa.Text(), nullable=False),  # ID técnico (ex: "gpt-4.1-mini")
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('default_temperature', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['provider_id'], ['llm_providers.id'], ),
        sa.UniqueConstraint('provider_id', 'model_id')
    )
    
    # Tabela de chaves API (criptografadas, por tenant + provider/model)
    op.create_table(
        'llm_api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=True),  # NULL = chave global para o provider
        sa.Column('encrypted_api_key', sa.Text(), nullable=False),
        sa.Column('base_url', sa.Text(), nullable=True),  # Para proxies ou custom endpoints
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['provider_id'], ['llm_providers.id'], ),
        sa.ForeignKeyConstraint(['model_id'], ['llm_models.id'], ),
        sa.UniqueConstraint('tenant_id', 'provider_id', 'model_id')
    )
    
    # Seed: Providers
    op.execute("""
        INSERT INTO llm_providers (id, name, slug, enabled) VALUES
        (1, 'OpenAI', 'openai', true),
        (2, 'Google Gemini', 'google', true),
        (3, 'Anthropic', 'anthropic', false),
        (4, 'Mistral', 'mistral', false),
        (5, 'Meta Llama', 'llama', false),
        (6, 'Local/Custom', 'local', false);
    """)
    
    # Seed: Models
    op.execute("""
        INSERT INTO llm_models (provider_id, name, model_id, enabled, default_temperature) VALUES
        -- OpenAI
        (1, 'GPT-4.1 Mini', 'gpt-4.1-mini', true, 0.7),
        (1, 'GPT-4.1 Nano', 'gpt-4.1-nano', true, 0.7),
        
        -- Google Gemini
        (2, 'Gemini 2.5 Flash', 'gemini-2.5-flash', true, 0.7),
        
        -- Anthropic (desabilitados por enquanto)
        (3, 'Claude 3.5 Sonnet', 'claude-3.5-sonnet', false, 0.7),
        (3, 'Claude 3.5 Haiku', 'claude-3.5-haiku', false, 0.7),
        
        -- Mistral (desabilitados por enquanto)
        (4, 'Mistral Large', 'mistral-large', false, 0.7),
        (4, 'Mistral Medium', 'mistral-medium', false, 0.7),
        
        -- Meta Llama (desabilitados por enquanto)
        (5, 'Llama 3.1 70B', 'llama-3.1-70b', false, 0.7),
        (5, 'Llama 3.1 8B', 'llama-3.1-8b', false, 0.7);
    """)

def downgrade():
    op.drop_table('llm_api_keys')
    op.drop_table('llm_models')
    op.drop_table('llm_providers')

