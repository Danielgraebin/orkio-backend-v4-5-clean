"""
RAG Events - ORKIO v3.7.0
Sistema de log de eventos RAG estruturados
"""

import logging
import time
from datetime import datetime
from sqlalchemy.orm import Session
from app.rag.models import RagEvent, RAG_EVENT_TYPES
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def log_event(
    db: Session,
    tenant_id: int,
    event_type: str,
    trace_id: Optional[str] = None,
    agent_id: Optional[int] = None,
    user_id: Optional[int] = None,
    doc_id: Optional[str] = None,
    status: Optional[str] = None,
    payload: Optional[Dict] = None,
    duration_ms: Optional[int] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    cost_usd: Optional[float] = None,
    citations: Optional[List[Dict]] = None
) -> RagEvent:
    """
    Registra um evento RAG com campos estruturados
    
    v3.7.0: Adiciona duration_ms, tokens, cost, citations
    """
    if event_type not in RAG_EVENT_TYPES:
        logger.warning(f"Unknown event type: {event_type}")
    
    event = RagEvent(
        tenant_id=tenant_id,
        trace_id=trace_id,
        type=event_type,
        agent_id=agent_id,
        user_id=user_id,
        doc_id=doc_id,
        status=status,
        payload=payload or {},
        duration_ms=duration_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        citations=citations or []
    )
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    logger.info(f"RAG event logged: {event_type} (trace={trace_id}, doc={doc_id}, duration={duration_ms}ms)")
    
    return event


class EventTimer:
    """
    Context manager para medir duração de operações
    
    Usage:
        with EventTimer() as timer:
            # operação
        duration_ms = timer.duration_ms
    """
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.duration_ms = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.duration_ms = int((self.end_time - self.start_time) * 1000)
        return False


def log_upload_flow(
    db: Session,
    tenant_id: int,
    trace_id: str,
    doc_id: str,
    user_id: int,
    filename: str,
    status: str,
    error: Optional[str] = None,
    duration_ms: Optional[int] = None
):
    """
    Log completo de fluxo de upload
    """
    if status == "start":
        log_event(
            db=db,
            tenant_id=tenant_id,
            event_type="upload_start",
            trace_id=trace_id,
            doc_id=doc_id,
            user_id=user_id,
            status="started",
            payload={"filename": filename}
        )
    
    elif status == "done":
        log_event(
            db=db,
            tenant_id=tenant_id,
            event_type="upload_done",
            trace_id=trace_id,
            doc_id=doc_id,
            user_id=user_id,
            status="success",
            payload={"filename": filename},
            duration_ms=duration_ms
        )
    
    elif status == "error":
        log_event(
            db=db,
            tenant_id=tenant_id,
            event_type="upload_error",
            trace_id=trace_id,
            doc_id=doc_id,
            user_id=user_id,
            status="failed",
            payload={"filename": filename, "error": error},
            duration_ms=duration_ms
        )


def log_vectorize_flow(
    db: Session,
    tenant_id: int,
    trace_id: str,
    doc_id: str,
    status: str,
    chunks_count: Optional[int] = None,
    error: Optional[str] = None,
    duration_ms: Optional[int] = None
):
    """
    Log completo de fluxo de vetorização
    """
    if status == "start":
        log_event(
            db=db,
            tenant_id=tenant_id,
            event_type="vectorize_start",
            trace_id=trace_id,
            doc_id=doc_id,
            status="started"
        )
    
    elif status == "done":
        log_event(
            db=db,
            tenant_id=tenant_id,
            event_type="vectorize_done",
            trace_id=trace_id,
            doc_id=doc_id,
            status="success",
            payload={"chunks_count": chunks_count},
            duration_ms=duration_ms
        )
    
    elif status == "error":
        log_event(
            db=db,
            tenant_id=tenant_id,
            event_type="vectorize_error",
            trace_id=trace_id,
            doc_id=doc_id,
            status="failed",
            payload={"error": error},
            duration_ms=duration_ms
        )


def log_chat_interaction(
    db: Session,
    tenant_id: int,
    trace_id: str,
    agent_id: int,
    user_id: int,
    query: str,
    answer: str,
    duration_ms: int,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    citations: List[Dict],
    model: str
):
    """
    Log completo de interação de chat
    """
    # Log query
    log_event(
        db=db,
        tenant_id=tenant_id,
        event_type="chat_query",
        trace_id=trace_id,
        agent_id=agent_id,
        user_id=user_id,
        status="success",
        payload={"query": query[:500], "model": model}
    )
    
    # Log answer
    log_event(
        db=db,
        tenant_id=tenant_id,
        event_type="chat_answer",
        trace_id=trace_id,
        agent_id=agent_id,
        user_id=user_id,
        status="success",
        payload={"answer": answer[:500], "model": model},
        duration_ms=duration_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        citations=citations
    )

