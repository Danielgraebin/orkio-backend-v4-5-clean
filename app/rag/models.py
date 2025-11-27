"""
RAG Models - ORKIO v3.7.0
Modelos de dados para RAG (eventos, links, documentos)
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Float, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.core.database import Base

class RagEvent(Base):
    """
    Tabela de eventos RAG para auditoria completa
    v3.7.0: Adiciona duration_ms, tokens, citations
    """
    __tablename__ = "rag_events"
    __table_args__ = ({'extend_existing': True},)
    
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    trace_id = Column(String(50), index=True)
    type = Column(String(50), nullable=False, index=True)
    agent_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    doc_id = Column(String(50), index=True)
    status = Column(String(20))
    payload = Column(JSON)
    
    # v3.7.0: Novos campos
    duration_ms = Column(Integer)  # Duração da operação
    prompt_tokens = Column(Integer)  # Tokens do prompt
    completion_tokens = Column(Integer)  # Tokens da resposta
    cost_usd = Column(Float)  # Custo estimado
    citations = Column(JSON)  # Lista de citações [{doc, chunk, score}]
    



class RagLink(Base):
    """
    Tabela de links entre agentes e documentos
    v3.7.0: Multi-vínculo sem reprocessamento
    """
    __tablename__ = "rag_links"
    __table_args__ = ({'extend_existing': True},)
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, nullable=False, index=True)
    doc_id = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer)  # user_id que criou o link
    
    __table_args__ = (
        UniqueConstraint('agent_id', 'doc_id', name='uq_agent_doc'),
    )


# Event Types v3.7.0
RAG_EVENT_TYPES = [
    # Upload
    "upload_start",
    "upload_done",
    "upload_error",
    
    # Parsing
    "parse_start",
    "parse_done",
    "parse_error",
    
    # Vectorization
    "vectorize_start",
    "vectorize_done",
    "vectorize_error",
    
    # Linking
    "link",
    "unlink",
    
    # Query
    "chat_query",
    "chat_answer",
    "chat_error",
    "chat_attachment",
    
    # Monitor
    "replay",
    
    # Legacy (manter compatibilidade)
    "rag.uploaded",
    "rag.parsed",
    "rag.chunked",
    "rag.embedded",
    "rag.embedding_failed",
    "rag.query",
    "rag.citation",
    "rag.answer_failed",
    "rag.linked_to_agent",
    "rag.unlinked_from_agent",
    "rag.deleted",
]

