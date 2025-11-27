import os
import logging
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.models import KnowledgeChunk, KnowledgeItem
from app.services.vectorize import get_embedding
import numpy as np

logger = logging.getLogger(__name__)

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    a_arr = np.array(a)
    b_arr = np.array(b)
    return np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr))

def search_knowledge(
    query: str,
    tenant_id: int,
    agent_ids: List[int] = None,
    top_k: int = 5,
    db: Session = None
) -> List[Dict]:
    """Search knowledge base using RAG"""
    if not db:
        return []
    
    # Get query embedding
    query_embedding = get_embedding(query)
    
    # Build query for knowledge items
    items_query = db.query(KnowledgeItem).filter(
        KnowledgeItem.tenant_id == tenant_id,
        KnowledgeItem.status == "vectorized",
        KnowledgeItem.deleted_at == None
    )
    
    # Get item_ids from document_agents if agent_ids provided (v3.8.0)
    if agent_ids:
        from sqlalchemy import text
        # Query document_agents to get linked documents
        doc_ids_result = db.execute(text("""
            SELECT DISTINCT document_id 
            FROM document_agents 
            WHERE agent_id = ANY(:agent_ids)
        """), {"agent_ids": agent_ids}).fetchall()
        
        linked_doc_ids = [row[0] for row in doc_ids_result]
        
        if linked_doc_ids:
            items_query = items_query.filter(KnowledgeItem.id.in_(linked_doc_ids))
        else:
            # No linked documents, return empty
            return []
    
    item_ids = [item.id for item in items_query.all()]
    
    if not item_ids:
        return []
    
    # Get all chunks for these items
    chunks = db.query(KnowledgeChunk).filter(
        KnowledgeChunk.item_id.in_(item_ids)
    ).all()
    
    # Calculate similarities
    results = []
    for chunk in chunks:
        if chunk.embedding:
            similarity = cosine_similarity(query_embedding, chunk.embedding)
            results.append({
                "chunk_id": chunk.id,
                "item_id": chunk.item_id,
                "text": chunk.text,
                "similarity": similarity
            })
    
    # Sort by similarity and return top_k
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]

