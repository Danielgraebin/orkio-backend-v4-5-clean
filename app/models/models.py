from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from pgvector.sqlalchemy import Vector
import enum
from datetime import datetime

class RoleEnum(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    USER = "USER"

# ===== MULTI-TENANCY =====

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    is_active = Column(Boolean, server_default="true", nullable=False)
    default_provider = Column(String(50), nullable=True)  # openai, anthropic, google, etc.
    allowed_models = Column(JSON, nullable=True)  # Lista de modelos permitidos para este tenant
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    memberships = relationship("Membership", back_populates="tenant")
    agents = relationship("Agent", back_populates="tenant")
    documents = relationship("Document", back_populates="tenant")
    conversations = relationship("Conversation", back_populates="tenant")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(Text, unique=True, nullable=False)
    hashed_password = Column(Text, nullable=False)
    status = Column(Text, server_default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    role = Column(Text, server_default="USER", nullable=False)  # USER, ADMIN, OWNER
    is_approved = Column(Boolean, server_default="false", nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    memberships = relationship("Membership", back_populates="user")

class Membership(Base):
    __tablename__ = "memberships"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    role = Column(Text, server_default="USER")
    
    __table_args__ = (UniqueConstraint("user_id", "tenant_id"),)
    
    user = relationship("User", back_populates="memberships")
    tenant = relationship("Tenant", back_populates="memberships")

# ===== AGENTS =====

class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(Text, nullable=False)
    system_prompt = Column(Text)
    provider = Column(Text, server_default="openai", nullable=False)  # openai, google, anthropic, manus
    model = Column(Text, server_default="gpt-4.1-mini", nullable=False)
    temperature = Column(Float, server_default="0.7")
    created_at = Column(DateTime, server_default=func.now())
    
    tenant = relationship("Tenant", back_populates="agents")
    documents = relationship("Document", back_populates="agent")
    conversations = relationship("Conversation", back_populates="agent")

# ===== RAG / KNOWLEDGE =====

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    filename = Column(Text, nullable=False)
    storage_path = Column(Text, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    status = Column(Text, server_default="PENDING", nullable=False)  # PENDING, PROCESSING, READY, ERROR
    tags = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    tenant = relationship("Tenant", back_populates="documents")
    agent = relationship("Agent", back_populates="documents")
    chunks = relationship("KnowledgeChunk", back_populates="document")

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, server_default="0", nullable=False)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime, server_default=func.now())
    
    document = relationship("Document", back_populates="chunks")

# ===== CONVERSATIONS =====

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    title = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    tenant = relationship("Tenant", back_populates="conversations")
    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("ConversationMessage", back_populates="conversation")
    rag_events = relationship("RAGEvent", back_populates="conversation")

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(Text, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    conversation = relationship("Conversation", back_populates="messages")

class RAGEvent(Base):
    __tablename__ = "rag_events"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("conversation_messages.id"), nullable=True)
    query = Column(Text)
    chunks_retrieved = Column(Integer, server_default="0")
    chunks_used = Column(Integer, server_default="0")
    created_at = Column(DateTime, server_default=func.now())
    
    conversation = relationship("Conversation", back_populates="rag_events")

# ===== MULTIAGENT =====

class AgentLink(Base):
    __tablename__ = "agent_links"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    from_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    to_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    trigger_keywords = Column(Text, nullable=True)  # JSON array
    priority = Column(Integer, server_default="0", nullable=False)
    active = Column(Boolean, server_default="true", nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class MultiagentSession(Base):
    __tablename__ = "multiagent_sessions"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    root_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    topic = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    messages = relationship("MultiagentMessage", back_populates="session")

class MultiagentMessage(Base):
    __tablename__ = "multiagent_messages"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("multiagent_sessions.id"), nullable=False)
    sender_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    receiver_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    content = Column(Text)
    model = Column(Text)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    
    session = relationship("MultiagentSession", back_populates="messages")

# ===== LLM PROVIDERS & MODELS =====

class LLMProvider(Base):
    __tablename__ = "llm_providers"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)  # OpenAI, Anthropic, Google, etc.
    provider_type = Column(String(50), nullable=False)  # openai, anthropic, google, manus
    api_key_encrypted = Column(Text, nullable=True)  # Encrypted API key
    api_base_url = Column(Text, nullable=True)  # Custom base URL (optional)
    is_active = Column(Boolean, server_default="true", nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    models = relationship("LLMModel", back_populates="provider")

class LLMModel(Base):
    __tablename__ = "llm_models"
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=False)
    name = Column(String(100), nullable=False)  # Display name (e.g., "GPT-4.1 Mini")
    model_id = Column(String(100), nullable=False)  # API model ID (e.g., "gpt-4.1-mini")
    max_tokens = Column(Integer, nullable=True)
    cost_per_1k_input_tokens = Column(Float, nullable=True)
    cost_per_1k_output_tokens = Column(Float, nullable=True)
    is_active = Column(Boolean, server_default="true", nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    provider = relationship("LLMProvider", back_populates="models")

