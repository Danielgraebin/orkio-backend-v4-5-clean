"""
Rotas User v4 - RAG Search
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user_v4
from app.services.rag_search import RAGSearchService

router = APIRouter()


@router.get("/rag/search")
async def search_documents(
    query: str = Query(..., description="Texto da busca"),
    conversation_id: Optional[int] = Query(None, description="ID da conversa (opcional)"),
    top_k: int = Query(3, ge=1, le=10, description="Número de resultados"),
    current_user = Depends(get_current_user_v4),
    db: Session = Depends(get_db)
):
    """
    Busca semântica em documentos processados.
    
    - Gera embedding da query
    - Busca chunks mais similares usando pgvector
    - Retorna documentos relevantes com scores
    """
    try:
        rag_service = RAGSearchService()
        
        if conversation_id:
            # Buscar por conversa
            results = rag_service.search_by_conversation(
                db, query, conversation_id, top_k
            )
        else:
            # Buscar em todos os documentos do tenant
            results = rag_service.search(
                db, query, current_user._tenant_id, top_k
            )
        
        return {
            "query": query,
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/rag/stats")
async def get_rag_stats(
    current_user = Depends(get_current_user_v4),
    db: Session = Depends(get_db)
):
    """
    Retorna estatísticas do RAG para o tenant.
    
    - Total de documentos
    - Documentos processados
    - Total de chunks
    """
    from app.models.models import Document, KnowledgeChunk
    
    total_docs = db.query(Document).filter(
        Document.tenant_id == current_user._tenant_id
    ).count()
    
    processed_docs = db.query(Document).filter(
        Document.tenant_id == current_user._tenant_id,
        Document.status == "COMPLETED"
    ).count()
    
    total_chunks = db.query(KnowledgeChunk).join(Document).filter(
        Document.tenant_id == current_user._tenant_id
    ).count()
    
    return {
        "total_documents": total_docs,
        "processed_documents": processed_docs,
        "total_chunks": total_chunks,
        "rag_enabled": processed_docs > 0
    }

