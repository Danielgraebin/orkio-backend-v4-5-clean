# services/rag_service.py
# v3.9.0: RAG real conforme patch
from sqlalchemy.orm import Session
from app.models.models import KnowledgeChunk, AgentDocument, TenantSettings, Agent
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

def get_tenant_settings(db: Session, tenant_id: int) -> dict:
    """Retorna configurações de modelo do tenant"""
    s = db.query(TenantSettings).filter(TenantSettings.tenant_id==tenant_id).first()
    return {
        "model": s.llm_model if s else "gpt-4o-mini",
        "temperature": s.llm_temperature if s else 0.2
    }

def retrieve_context(db: Session, tenant_id: int, agent_id: int, query: str, k: int = 4) -> Tuple[List[str], int]:
    """
    Recupera chunks dos documentos vinculados ao agent_id.
    v3.9.0: Usa agent_documents (N:N)
    
    Returns:
        (context_blocks, hit_count)
    """
    try:
        # Buscar chunks dos documentos vinculados
        q = db.query(KnowledgeChunk, AgentDocument).join(
            AgentDocument, AgentDocument.document_id==KnowledgeChunk.item_id
        ).filter(
            AgentDocument.agent_id==agent_id
        )
        
        # Buscar todos os chunks (limite 200 para performance)
        chunks = [(c.text, c.embedding) for (c, _) in q.limit(200).all()]
        
        if not chunks:
            logger.info(f"RAG: No chunks found for agent_id={agent_id}")
            return [], 0
        
        # Ranking simples por substring (TODO: usar similaridade cosseno)
        texts = [c[0] for c in chunks]
        query_lower = query.lower()
        scored = sorted(
            texts, 
            key=lambda t: sum(1 for w in query_lower.split() if w in t.lower()), 
            reverse=True
        )
        
        top_k = scored[:k]
        logger.info(f"RAG: Retrieved {len(top_k)} chunks for agent_id={agent_id}")
        
        return top_k, len(scored)
    
    except Exception as e:
        logger.error(f"RAG retrieve_context failed: {e}")
        return [], 0

