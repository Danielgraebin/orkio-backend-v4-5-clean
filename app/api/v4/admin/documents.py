"""
Rotas Admin v4 - Documents (Knowledge Base)
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import os
from datetime import datetime

from app.core.database import get_db
from app.models.models import Document, Agent, Membership, KnowledgeChunk
from app.core.auth_v4 import get_current_user, CurrentUser
from app.services.document_processor import DocumentProcessor

router = APIRouter(prefix="/admin")


class DocumentResponse(BaseModel):
    id: int
    agent_id: int
    agent_name: str
    filename: str
    size_kb: int
    chunks: int
    created_at: str
    
    class Config:
        from_attributes = True


@router.get("/documents", response_model=dict)
def list_documents(
    agent_id: Optional[int] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista documentos do tenant, com filtro opcional por agente.
    """
    # Verificar permissão
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not membership or membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    
    # Query base
    query = db.query(Document, Agent).join(
        Agent, Document.agent_id == Agent.id
    ).filter(
        Document.tenant_id == current_user.tenant_id
    )
    
    # Filtro por agente
    if agent_id:
        query = query.filter(Document.agent_id == agent_id)
    
    results = query.all()
    
    documents = []
    for doc, agent in results:
        # Contar chunks
        chunks_count = db.query(KnowledgeChunk).filter(
            KnowledgeChunk.document_id == doc.id
        ).count()
        
        documents.append({
            "id": doc.id,
            "agent_id": agent.id,
            "agent_name": agent.name,
            "filename": doc.filename,
            "size_kb": doc.size_bytes // 1024 if doc.size_bytes else 0,
            "chunks": chunks_count,
            "created_at": doc.created_at.isoformat() if doc.created_at else None
        })
    
    return {"documents": documents}


@router.post("/documents/upload", response_model=dict, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    agent_id: int = Form(...),
    tags: Optional[str] = Form(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload de documento e processamento para RAG com chunking e embeddings REAIS.
    
    Processo:
    1. Extrai texto (PDF/TXT/DOCX)
    2. Cria chunks (800 tokens, 200 overlap)
    3. Gera embeddings OpenAI (text-embedding-3-small)
    4. Armazena no pgvector
    """
    # Verificar permissão
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not membership or membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    
    # Verificar se agente existe e pertence ao tenant
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.tenant_id == current_user.tenant_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Ler conteúdo do arquivo
    content = await file.read()
    size_bytes = len(content)
    
    # Salvar arquivo temporariamente
    storage_path = f"/tmp/orkio_docs/{current_user.tenant_id}/{file.filename}"
    os.makedirs(os.path.dirname(storage_path), exist_ok=True)
    
    with open(storage_path, "wb") as f:
        f.write(content)
    
    # Criar documento no banco com status PROCESSING
    document = Document(
        tenant_id=current_user.tenant_id,
        agent_id=agent_id,
        filename=file.filename,
        storage_path=storage_path,
        size_bytes=size_bytes,
        tags=tags,
        status="PROCESSING"  # Indica que está sendo processado
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    try:
        # Processar documento: extrair texto, chunking, embeddings
        processor = DocumentProcessor()
        chunk_texts, chunk_embeddings = processor.process_document(storage_path, file.filename)
        
        # Criar chunks no banco com embeddings
        for idx, (chunk_text, embedding) in enumerate(zip(chunk_texts, chunk_embeddings)):
            chunk = KnowledgeChunk(
                document_id=document.id,
                content=chunk_text,
                chunk_index=idx,
                embedding=embedding  # pgvector armazena como ARRAY
            )
            db.add(chunk)
        
        # Atualizar status do documento para READY
        document.status = "READY"
        db.commit()
        
        chunks_count = len(chunk_texts)
        
    except Exception as e:
        # Em caso de erro, marcar documento como ERROR
        document.status = "ERROR"
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar documento: {str(e)}"
        )
    
    return {
        "document": {
            "id": document.id,
            "agent_id": agent.id,
            "agent_name": agent.name,
            "filename": document.filename,
            "size_kb": size_bytes // 1024,
            "chunks": chunks_count,
            "created_at": document.created_at.isoformat() if document.created_at else None
        }
    }


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove documento + chunks + embeddings.
    """
    # Verificar permissão
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not membership or membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    
    # Buscar documento
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Deletar chunks
    db.query(KnowledgeChunk).filter(
        KnowledgeChunk.document_id == document_id
    ).delete()
    
    # Deletar arquivo físico
    if document.storage_path and os.path.exists(document.storage_path):
        os.remove(document.storage_path)
    
    # Deletar documento
    db.delete(document)
    db.commit()
    
    return None


@router.get("/documents/{document_id}/chunks", response_model=dict)
def get_document_chunks(
    document_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Debug: mostra chunks de um documento.
    """
    # Verificar permissão
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not membership or membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    
    # Buscar documento
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Buscar chunks
    chunks = db.query(KnowledgeChunk).filter(
        KnowledgeChunk.document_id == document_id
    ).order_by(KnowledgeChunk.chunk_index).all()
    
    chunks_list = []
    for chunk in chunks:
        chunks_list.append({
            "id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
            "created_at": chunk.created_at.isoformat() if chunk.created_at else None
        })
    
    return {
        "document_id": document_id,
        "filename": document.filename,
        "chunks": chunks_list
    }

