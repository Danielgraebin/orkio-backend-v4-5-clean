"""
RAG Monitor - ORKIO v3.7.0
Queries de auditoria e análise de eventos RAG
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.rag.models import RagEvent, RagLink
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def get_overview(db: Session, tenant_id: int, days: int = 30) -> Dict:
    """
    Retorna overview de métricas RAG
    v3.7.0: Adiciona métricas de custo e tokens
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Total de documentos
    from app.models.models import KnowledgeItem
    total_docs = db.query(func.count(KnowledgeItem.id)).filter(
        KnowledgeItem.tenant_id == tenant_id,
        KnowledgeItem.status == "vectorized"
    ).scalar() or 0
    
    # Total de chunks
    from app.models.models import KnowledgeChunk
    total_chunks = db.query(func.count(KnowledgeChunk.id)).join(
        KnowledgeItem, KnowledgeChunk.item_id == KnowledgeItem.id
    ).filter(
        KnowledgeItem.tenant_id == tenant_id
    ).scalar() or 0
    
    # Total de queries
    total_queries = db.query(func.count(RagEvent.id)).filter(
        RagEvent.tenant_id == tenant_id,
        RagEvent.type.in_(["chat_query", "rag.query"]),
        RagEvent.ts >= cutoff
    ).scalar() or 0
    
    # Total de erros
    total_errors = db.query(func.count(RagEvent.id)).filter(
        RagEvent.tenant_id == tenant_id,
        RagEvent.type.like("%_error"),
        RagEvent.ts >= cutoff
    ).scalar() or 0
    
    # Custo total
    total_cost = db.query(func.sum(RagEvent.cost_usd)).filter(
        RagEvent.tenant_id == tenant_id,
        RagEvent.cost_usd.isnot(None),
        RagEvent.ts >= cutoff
    ).scalar() or 0.0
    
    # Tokens totais
    total_prompt_tokens = db.query(func.sum(RagEvent.prompt_tokens)).filter(
        RagEvent.tenant_id == tenant_id,
        RagEvent.prompt_tokens.isnot(None),
        RagEvent.ts >= cutoff
    ).scalar() or 0
    
    total_completion_tokens = db.query(func.sum(RagEvent.completion_tokens)).filter(
        RagEvent.tenant_id == tenant_id,
        RagEvent.completion_tokens.isnot(None),
        RagEvent.ts >= cutoff
    ).scalar() or 0
    
    # Top documentos (mais citados)
    top_docs_raw = db.query(
        func.jsonb_array_elements(RagEvent.citations).op('->')('doc').as_string().label('doc'),
        func.count().label('count')
    ).filter(
        RagEvent.tenant_id == tenant_id,
        RagEvent.citations.isnot(None),
        RagEvent.ts >= cutoff
    ).group_by('doc').order_by(func.count().desc()).limit(10).all()
    
    top_docs = [{"doc": d[0].strip('"'), "count": d[1]} for d in top_docs_raw]
    
    # Top agentes (mais usados)
    top_agents = db.query(
        RagEvent.agent_id,
        func.count(RagEvent.id).label("count")
    ).filter(
        RagEvent.tenant_id == tenant_id,
        RagEvent.type.in_(["chat_query", "rag.query"]),
        RagEvent.ts >= cutoff,
        RagEvent.agent_id.isnot(None)
    ).group_by(RagEvent.agent_id).order_by(func.count(RagEvent.id).desc()).limit(10).all()
    
    return {
        "total_docs": total_docs,
        "total_chunks": total_chunks,
        "total_queries": total_queries,
        "total_errors": total_errors,
        "total_cost_usd": round(total_cost, 4),
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "top_docs": top_docs,
        "top_agents": [{"agent_id": a[0], "count": a[1]} for a in top_agents],
        "period_days": days
    }


def get_events(
    db: Session,
    tenant_id: int,
    event_type: Optional[str] = None,
    agent_id: Optional[int] = None,
    doc_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    user_id: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50
) -> Dict:
    """
    Retorna eventos RAG com filtros
    v3.7.0: Adiciona filtro por user_id
    """
    query = db.query(RagEvent).filter(RagEvent.tenant_id == tenant_id)
    
    if event_type:
        query = query.filter(RagEvent.type == event_type)
    
    if agent_id:
        query = query.filter(RagEvent.agent_id == agent_id)
    
    if doc_id:
        query = query.filter(RagEvent.doc_id == doc_id)
    
    if trace_id:
        query = query.filter(RagEvent.trace_id == trace_id)
    
    if user_id:
        query = query.filter(RagEvent.user_id == user_id)
    
    if from_date:
        query = query.filter(RagEvent.ts >= from_date)
    
    if to_date:
        query = query.filter(RagEvent.ts <= to_date)
    
    total = query.count()
    
    events = query.order_by(RagEvent.ts.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "events": [
            {
                "id": e.id,
                "ts": e.ts.isoformat() if e.ts else None,
                "trace_id": e.trace_id,
                "type": e.type,
                "agent_id": e.agent_id,
                "user_id": e.user_id,
                "doc_id": e.doc_id,
                "status": e.status,
                "payload": e.payload,
                "duration_ms": e.duration_ms,
                "prompt_tokens": e.prompt_tokens,
                "completion_tokens": e.completion_tokens,
                "cost_usd": e.cost_usd,
                "citations": e.citations
            }
            for e in events
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }


def get_session(db: Session, tenant_id: int, trace_id: str) -> Dict:
    """
    Retorna timeline consolidada de um trace_id
    v3.7.0: Inclui todos campos novos
    """
    events = db.query(RagEvent).filter(
        RagEvent.tenant_id == tenant_id,
        RagEvent.trace_id == trace_id
    ).order_by(RagEvent.ts).all()
    
    return {
        "trace_id": trace_id,
        "events": [
            {
                "id": e.id,
                "ts": e.ts.isoformat() if e.ts else None,
                "type": e.type,
                "agent_id": e.agent_id,
                "user_id": e.user_id,
                "doc_id": e.doc_id,
                "status": e.status,
                "payload": e.payload,
                "duration_ms": e.duration_ms,
                "prompt_tokens": e.prompt_tokens,
                "completion_tokens": e.completion_tokens,
                "cost_usd": e.cost_usd,
                "citations": e.citations
            }
            for e in events
        ],
        "total_events": len(events)
    }


def link_agent_to_doc(db: Session, agent_id: int, doc_id: str, user_id: int) -> RagLink:
    """
    Cria link entre agente e documento
    v3.7.0: Adiciona created_by
    """
    # Verificar se já existe
    existing = db.query(RagLink).filter(
        RagLink.agent_id == agent_id,
        RagLink.doc_id == doc_id
    ).first()
    
    if existing:
        return existing
    
    link = RagLink(agent_id=agent_id, doc_id=doc_id, created_by=user_id)
    db.add(link)
    db.commit()
    db.refresh(link)
    
    logger.info(f"Linked agent {agent_id} to doc {doc_id} by user {user_id}")
    
    return link


def unlink_agent_from_doc(db: Session, agent_id: int, doc_id: str) -> bool:
    """
    Remove link entre agente e documento
    """
    link = db.query(RagLink).filter(
        RagLink.agent_id == agent_id,
        RagLink.doc_id == doc_id
    ).first()
    
    if link:
        db.delete(link)
        db.commit()
        logger.info(f"Unlinked agent {agent_id} from doc {doc_id}")
        return True
    
    return False


def get_agent_docs(db: Session, agent_id: int) -> List[str]:
    """
    Retorna lista de doc_ids linkados a um agente
    """
    links = db.query(RagLink.doc_id).filter(RagLink.agent_id == agent_id).all()
    return [link[0] for link in links]


def get_doc_agents(db: Session, doc_id: str) -> List[int]:
    """
    Retorna lista de agent_ids linkados a um documento
    """
    links = db.query(RagLink.agent_id).filter(RagLink.doc_id == doc_id).all()
    return [link[0] for link in links]

