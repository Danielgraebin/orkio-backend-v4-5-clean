# Orkio RAG Service v3.7.x
# Adaptado do patch do Dev (sem pgvector, usa cosseno em Python)

from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import numpy as np

from app.models.models import Agent, KnowledgeItem, KnowledgeChunk, AgentDocument, RagEvent
from app.services.llm import embed_texts

# --- RAG Events (usar SQL direto para compatibilidade) ---
def log_rag_event(db: Session, *, tenant_id: int, agent_id: int, document_id: Optional[str],
                  query: str, hit_count: int, latency_ms: int, reason: Optional[str] = None):
    """Log RAG event usando SQL direto (compatível com schema existente)."""
    try:
        db.execute(text("""
            INSERT INTO rag_events (tenant_id, agent_id, document_id, query, hit_count, latency_ms, ts, reason)
            VALUES (:tenant_id, :agent_id, :document_id, :query, :hit_count, :latency_ms, NOW(), :reason)
        """), {
            'tenant_id': tenant_id,
            'agent_id': agent_id,
            'document_id': document_id,
            'query': query,
            'hit_count': hit_count,
            'latency_ms': latency_ms,
            'reason': reason
        })
        db.commit()
    except Exception as e:
        # Silenciar erro de log para não quebrar RAG
        db.rollback()
        pass

# --- Similaridade Cosseno ---
def cosine_similarity(a: list, b: list) -> float:
    """Calcula similaridade cosseno entre dois vetores."""
    if not a or not b:
        return 0.0
    a_np = np.array(a)
    b_np = np.array(b)
    dot = np.dot(a_np, b_np)
    norm_a = np.linalg.norm(a_np)
    norm_b = np.linalg.norm(b_np)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

# --- Semantic Retrieval (sem pgvector) ---
def retrieve_context(db: Session, *, tenant_id: int, agent_id: int,
                     query: str, limit: int = 5) -> Tuple[List[str], int]:
    """
    Busca semântica usando embeddings + cosseno.
    
    Returns:
        (context_blocks, hit_count)
    """
    start_time = datetime.utcnow()
    
    # 1. Embed query (usar mesmo modelo dos documentos)
    q_embedding = embed_texts([query], model="text-embedding-3-small")
    if not q_embedding or not q_embedding[0]:
        # Fallback: sem embedding, retorna vazio
        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        log_rag_event(db, tenant_id=tenant_id, agent_id=agent_id, document_id=None,
                     query=query, hit_count=0, latency_ms=latency_ms, reason="Embedding falhou")
        return [], 0
    
    q_emb = q_embedding[0]
    
    # 2. Buscar documentos vinculados ao agente
    doc_ids = db.query(AgentDocument.document_id).filter(
        AgentDocument.agent_id == agent_id
    ).all()
    doc_ids = [d[0] for d in doc_ids]
    
    if not doc_ids:
        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        log_rag_event(db, tenant_id=tenant_id, agent_id=agent_id, document_id=None,
                     query=query, hit_count=0, latency_ms=latency_ms, reason="Nenhum documento vinculado")
        return [], 0
    
    # 3. Buscar chunks dos documentos vinculados
    chunks = db.query(KnowledgeChunk).filter(
        KnowledgeChunk.item_id.in_(doc_ids)
    ).all()
    
    if not chunks:
        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        log_rag_event(db, tenant_id=tenant_id, agent_id=agent_id, document_id=None,
                     query=query, hit_count=0, latency_ms=latency_ms, reason="Nenhum chunk encontrado")
        return [], 0
    
    # 4. Calcular similaridade para cada chunk
    scored_chunks = []
    for chunk in chunks:
        if not chunk.embedding:
            continue
        
        # Parse embedding (pode ser JSON string ou lista)
        try:
            if isinstance(chunk.embedding, str):
                emb = json.loads(chunk.embedding)
            else:
                emb = chunk.embedding
        except:
            continue
        
        # Filtrar apenas chunks com dimensão compatível
        if len(emb) != len(q_emb):
            continue
        
        score = cosine_similarity(q_emb, emb)
        scored_chunks.append((score, chunk.text, chunk.item_id))
    
    # 5. Ordenar por score DESC e pegar top-K
    scored_chunks.sort(reverse=True, key=lambda x: x[0])
    top_chunks = scored_chunks[:limit]
    
    # 6. Extrair contexto
    context_blocks = [chunk_text for (score, chunk_text, doc_id) in top_chunks]
    hit_count = len(context_blocks)
    
    # 7. Log evento
    latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    doc_id_hit = top_chunks[0][2] if top_chunks else None
    log_rag_event(db, tenant_id=tenant_id, agent_id=agent_id, document_id=doc_id_hit,
                 query=query, hit_count=hit_count, latency_ms=latency_ms)
    
    return context_blocks, hit_count

# --- Circuit Breaker ---
def should_call_llm(use_rag: bool, hits: int, allow_fallback: bool = True) -> bool:
    """
    Decide se deve chamar LLM.
    
    Se use_rag=TRUE e hits=0 e allow_fallback=FALSE → não chamar LLM.
    """
    if use_rag and hits == 0 and not allow_fallback:
        return False
    return True

