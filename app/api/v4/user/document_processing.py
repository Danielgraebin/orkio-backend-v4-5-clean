"""
Rotas User v4 - Document Processing (RAG)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import traceback

from app.core.database import get_db
from app.models.models import Document, KnowledgeChunk
from app.core.security import get_current_user_v4
from app.services.document_processor import DocumentProcessor

router = APIRouter()


@router.post("/documents/{document_id}/process")
async def process_document(
    document_id: int,
    current_user = Depends(get_current_user_v4),
    db: Session = Depends(get_db)
):
    """
    Processa um documento: extrai texto, cria chunks e gera embeddings.
    
    - Valida que documento pertence ao tenant do usuário
    - Usa DocumentProcessor para processar
    - Salva chunks no banco com embeddings
    - Atualiza status do documento
    """
    try:
        # Buscar documento
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == current_user._tenant_id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found or does not belong to tenant"
            )
        
        # Verificar se já foi processado
        if document.status == "COMPLETED":
            return {
                "message": "Document already processed",
                "document_id": document_id,
                "status": "COMPLETED",
                "chunks_count": document.chunks_count
            }
        
        # Atualizar status para PROCESSING
        document.status = "PROCESSING"
        db.commit()
        
        # Processar documento
        processor = DocumentProcessor()
        
        try:
            chunk_texts, embeddings = processor.process_document(
                document.storage_path,
                document.filename
            )
            
            # Salvar chunks no banco
            chunks_created = 0
            for i, (text, embedding) in enumerate(zip(chunk_texts, embeddings)):
                chunk = KnowledgeChunk(
                    document_id=document.id,
                    content=text,
                    embedding=embedding,
                    chunk_index=i
                )
                db.add(chunk)
                chunks_created += 1
            
            # Atualizar documento
            document.status = "COMPLETED"
            document.chunks_count = chunks_created
            db.commit()
            
            return {
                "message": "Document processed successfully",
                "document_id": document_id,
                "status": "COMPLETED",
                "chunks_count": chunks_created
            }
            
        except Exception as e:
            # Erro no processamento
            document.status = "ERROR"
            document.error_message = str(e)
            db.commit()
            
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process document: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
        )


@router.get("/documents")
async def list_documents(
    current_user = Depends(get_current_user_v4),
    db: Session = Depends(get_db)
):
    """
    Lista todos os documentos do tenant do usuário.
    """
    documents = db.query(Document).filter(
        Document.tenant_id == current_user._tenant_id
    ).order_by(Document.created_at.desc()).all()
    
    return {
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "status": doc.status,
                "chunks_count": doc.chunks_count or 0,
                "size_kb": round(doc.size_bytes / 1024, 2) if doc.size_bytes else 0,
                "created_at": doc.created_at.isoformat(),
                "error_message": doc.error_message if hasattr(doc, 'error_message') else None
            }
            for doc in documents
        ]
    }


@router.get("/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: int,
    current_user = Depends(get_current_user_v4),
    db: Session = Depends(get_db)
):
    """
    Lista todos os chunks de um documento.
    """
    # Verificar se documento existe e pertence ao tenant
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user._tenant_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found or does not belong to tenant"
        )
    
    # Buscar chunks
    chunks = db.query(KnowledgeChunk).filter(
        KnowledgeChunk.document_id == document_id
    ).order_by(KnowledgeChunk.chunk_index).all()
    
    return {
        "document_id": document_id,
        "filename": document.filename,
        "chunks_count": len(chunks),
        "chunks": [
            {
                "id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                "content_length": len(chunk.content)
            }
            for chunk in chunks
        ]
    }

