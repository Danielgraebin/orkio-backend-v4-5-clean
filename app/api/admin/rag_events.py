# app/api/admin/rag_events.py
# v3.10.0: Endpoint para painel Hive (RAG)

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.models import User
from app.core.security import get_current_user
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/rag/events")
def list_rag_events(
    conversation_id: Optional[int] = Query(None),
    agent_id: Optional[int] = Query(None),
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user)
):
    """
    Listar eventos RAG.
    GET /admin/rag/events?conversation_id=123&limit=50
    """
    try:
        # Construir query dinamicamente
        where_clauses = []
        params = {}
        
        if conversation_id:
            where_clauses.append("conversation_id = :conversation_id")
            params['conversation_id'] = conversation_id
        
        if agent_id:
            where_clauses.append("agent_id = :agent_id")
            params['agent_id'] = agent_id
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
            SELECT 
                id,
                ts,
                tenant_id,
                agent_id,
                document_id,
                query,
                hit_count,
                latency_ms,
                reason,
                status
            FROM rag_events
            WHERE {where_sql}
            ORDER BY ts DESC
            LIMIT :limit
        """
        
        params['limit'] = limit
        
        result = db.execute(text(query), params)
        
        events = []
        for row in result:
            events.append({
                "id": row.id,
                "ts": str(row.ts),
                "tenant_id": row.tenant_id,
                "agent_id": row.agent_id,
                "document_id": row.document_id,
                "query": row.query,
                "hit_count": row.hit_count,
                "latency_ms": row.latency_ms,
                "reason": row.reason,
                "status": row.status
            })
        
        return {"events": events, "count": len(events)}
        
    except Exception as e:
        logger.exception("List RAG events failed")
        return {"events": [], "count": 0, "error": str(e)}

