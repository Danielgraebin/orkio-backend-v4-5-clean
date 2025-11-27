# api/knowledge.py
# v3.9.0: Endpoints admin knowledge conforme patch
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import KnowledgeItem, Agent, AgentDocument
from app.core.security import get_current_user
from app.services.knowledge import extract_text, vectorize_document
import uuid
import hashlib
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    tags: Optional[str] = Form(""),
    link_agent_ids: Optional[str] = Form(None),  # "1,2,3"
    db: Session = Depends(get_db),
    admin = Depends(get_current_user),
):
    """
    Upload documento e vetoriza.
    v3.9.0: Usa agent_documents (N:N) e services/knowledge.py
    """
    try:
        raw = await file.read()
        
        # Criar documento
        doc_id = str(uuid.uuid4())
        doc = KnowledgeItem(
            id=doc_id,
            tenant_id=1,  # Admin tenant stub
            filename=file.filename,
            mime=file.content_type,
            size=len(raw),
            tags=[t.strip() for t in tags.split(",") if t.strip()],
            checksum=hashlib.sha256(raw).hexdigest(),
            status="processing",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Extrair + vetorizar
        try:
            text = extract_text(file, raw)
            result = vectorize_document(db, 1, doc.id, text)
        except Exception as e:
            db.query(KnowledgeItem).filter(KnowledgeItem.id==doc.id).update({"status": "error", "error_reason": str(e)})
            db.commit()
            raise HTTPException(status_code=500, detail=f"vectorization_failed: {e}")

        # Criar vínculos N:N
        if link_agent_ids:
            ids = [int(x) for x in link_agent_ids.split(",") if x.strip().isdigit()]
            for aid in ids:
                agent = db.query(Agent).filter(Agent.id==aid).first()
                if agent:
                    # ON CONFLICT DO NOTHING via try/except
                    try:
                        db.add(AgentDocument(agent_id=aid, document_id=doc.id))
                        db.commit()
                    except Exception:
                        db.rollback()  # Ignora duplicatas

        return {"id": doc.id, "status": "vectorized", "chunks": result.chunks}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
def list_documents(db: Session = Depends(get_db), admin = Depends(get_current_user)):
    """
    Lista documentos com linked_agents.
    v3.9.0: Lê de agent_documents
    """
    docs = db.query(KnowledgeItem).filter(
        KnowledgeItem.tenant_id==1,
        KnowledgeItem.deleted_at==None
    ).order_by(KnowledgeItem.created_at.desc()).all()
    
    out = []
    for d in docs:
        # Buscar agentes vinculados
        links = db.query(AgentDocument, Agent).join(
            Agent, Agent.id==AgentDocument.agent_id
        ).filter(AgentDocument.document_id==d.id).all()
        
        out.append({
            "id": d.id,
            "filename": d.filename,
            "size_kb": round(d.size / 1024) if d.size else 0,
            "status": d.status,
            "chunks": d.chunks_count,
            "uploaded_at": d.created_at.isoformat() if d.created_at else None,
            "linked_agents": [{"id": a.id, "name": a.name} for (_, a) in links],
            "tags": d.tags or []
        })
    
    return {"items": out, "total": len(out)}

@router.post("/agents/{agent_id}/documents/{doc_id}")
def link_doc(agent_id: int, doc_id: str, db: Session = Depends(get_db), admin = Depends(get_current_user)):
    """Link documento a agente (N:N)"""
    exists = db.query(AgentDocument).filter_by(agent_id=agent_id, document_id=doc_id).first()
    if not exists:
        db.add(AgentDocument(agent_id=agent_id, document_id=doc_id))
        db.commit()
    return {"linked": True}

@router.delete("/agents/{agent_id}/documents/{doc_id}")
def unlink_doc(agent_id: int, doc_id: str, db: Session = Depends(get_db), admin = Depends(get_current_user)):
    """Unlink documento de agente"""
    db.query(AgentDocument).filter_by(agent_id=agent_id, document_id=doc_id).delete()
    db.commit()
    return {"linked": False}



# --- P0: Endpoints de vínculo e delete ---

from pydantic import BaseModel

class LinkAgentsRequest(BaseModel):
    agent_ids: List[int]

@router.post("/{document_id}/link")
def link_agents_to_document(
    document_id: str,
    payload: LinkAgentsRequest,
    db: Session = Depends(get_db),
    admin = Depends(get_current_user)
):
    """
    Vincular múltiplos agentes a um documento.
    POST /admin/knowledge/{document_id}/link
    Body: {"agent_ids": [1, 2, 3]}
    """
    # Verificar se documento existe
    doc = db.query(KnowledgeItem).filter(KnowledgeItem.id==document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="document_not_found")
    
    # Vincular agentes
    linked_count = 0
    for agent_id in payload.agent_ids:
        # Verificar se agente existe
        agent = db.query(Agent).filter(Agent.id==agent_id).first()
        if not agent:
            continue
        
        # Inserir vínculo (ON CONFLICT DO NOTHING)
        exists = db.query(AgentDocument).filter_by(
            agent_id=agent_id, 
            document_id=document_id
        ).first()
        
        if not exists:
            db.add(AgentDocument(agent_id=agent_id, document_id=document_id))
            linked_count += 1
    
    db.commit()
    return {"linked": True, "count": linked_count}

@router.post("/{document_id}/unlink")
def unlink_agents_from_document(
    document_id: str,
    payload: LinkAgentsRequest,
    db: Session = Depends(get_db),
    admin = Depends(get_current_user)
):
    """
    Desvincular múltiplos agentes de um documento.
    POST /admin/knowledge/{document_id}/unlink
    Body: {"agent_ids": [1, 2, 3]}
    """
    unlinked_count = 0
    for agent_id in payload.agent_ids:
        result = db.query(AgentDocument).filter_by(
            agent_id=agent_id,
            document_id=document_id
        ).delete()
        unlinked_count += result
    
    db.commit()
    return {"unlinked": True, "count": unlinked_count}

@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    admin = Depends(get_current_user)
):
    """
    Deletar documento com cascata.
    DELETE /admin/knowledge/{document_id}
    
    Remove:
    - knowledge_items
    - agent_documents (FK CASCADE)
    - knowledge_chunks (FK CASCADE)
    """
    from app.models.models import KnowledgeChunk
    from sqlalchemy import text
    
    # Verificar se documento existe
    doc = db.query(KnowledgeItem).filter(KnowledgeItem.id==document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="document_not_found")
    
    try:
        # Deletar chunks (se não tiver FK CASCADE)
        db.query(KnowledgeChunk).filter(KnowledgeChunk.item_id==document_id).delete()
        
        # Deletar vínculos (se não tiver FK CASCADE)
        db.query(AgentDocument).filter(AgentDocument.document_id==document_id).delete()
        
        # Deletar documento
        db.delete(doc)
        
        db.commit()
        return {"deleted": True, "document_id": document_id}
        
    except Exception as e:
        db.rollback()
        logger.exception("Delete failed")
        raise HTTPException(status_code=500, detail=f"delete_failed: {str(e)}")

