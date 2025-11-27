"""ORKIO v4.0 - Initial Schema

Revision ID: 0001_initial
Revises: 
Create Date: 2025-11-14 08:35:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Criar extensão pgvector (já criada manualmente, mas garantir)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Tabela: tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()"))
    )
    
    # Tabela: users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.Text, unique=True, nullable=False),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()"))
    )
    
    # Tabela: memberships
    op.create_table(
        "memberships",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("role", sa.Text, server_default="USER"),
        sa.UniqueConstraint("user_id", "tenant_id")
    )
    
    # Tabela: agents
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("system_prompt", sa.Text),
        sa.Column("temperature", sa.Float, server_default="0.7"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()"))
    )
    
    # Tabela: documents
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("agent_id", sa.Integer, sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()"))
    )
    
    # Tabela: knowledge_chunks (com pgvector)
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("chunk", sa.Text, nullable=False),
        sa.Column("embedding", Vector(1536)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()"))
    )
    
    # Índice ivfflat para busca vetorial
    op.create_index(
        "idx_embeddings",
        "knowledge_chunks",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_ops={"embedding": "vector_cosine_ops"}
    )
    
    # Tabela: conversations
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("agent_id", sa.Integer, sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("title", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()"))
    )
    
    # Tabela: conversation_messages
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conversation_id", sa.Integer, sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()"))
    )
    
    # Tabela: rag_events
    op.create_table(
        "rag_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conversation_id", sa.Integer, sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("query", sa.Text),
        sa.Column("top_k", sa.Integer),
        sa.Column("used_chunks", sa.JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()"))
    )
    
    # Tabela: multiagent_sessions
    op.create_table(
        "multiagent_sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("root_agent_id", sa.Integer, sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("topic", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()"))
    )
    
    # Tabela: multiagent_messages
    op.create_table(
        "multiagent_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("multiagent_sessions.id"), nullable=False),
        sa.Column("sender_agent_id", sa.Integer, sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("receiver_agent_id", sa.Integer, sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("content", sa.Text),
        sa.Column("model", sa.Text),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()"))
    )


def downgrade():
    op.drop_table("multiagent_messages")
    op.drop_table("multiagent_sessions")
    op.drop_table("rag_events")
    op.drop_table("conversation_messages")
    op.drop_table("conversations")
    op.drop_index("idx_embeddings", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_table("documents")
    op.drop_table("agents")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("tenants")

