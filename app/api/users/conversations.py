_# app/api/users/conversations.py
# v4.5: Endpoints de threads (conversations) com multi-tenant
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, get_current_user_tenant
from app.models.models import User, Conversation, ConversationMessage, KnowledgeItem, AgentDocument
from app.services.knowledge import extract_text, vectorize_document
from typing import List, Optional
import logging
import uuid
import hashlib

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Models ---

class CreateConversationRequest(BaseModel):
    agent_id: int
    title: Optional[str] = None

class ConversationResponse(BaseModel):
    id: int
    agent_id: int
    title: Optional[str]
    created_at: str
    message_count: int

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str

class UpdateConversationRequest(BaseModel):
    title: str

# --- Endpoints ---

@router.post("/conversations", tags=["User Console - Conversations"])
def create_conversation(
    payload: CreateConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    new_conversation = Conversation(
        tenant_id=tenant_id,
        agent_id=payload.agent_id,
        user_id=current_user.id,
        title=payload.title or "Nova conversa"
    )
    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)
    return new_conversation

@router.get("/conversations", response_model=List[ConversationResponse], tags=["User Console - Conversations"])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    conversations = db.query(Conversation).filter(
        Conversation.tenant_id == tenant_id,
        Conversation.user_id == current_user.id
    ).order_by(Conversation.created_at.desc()).all()
    
    response = []
    for conv in conversations:
        message_count = len(conv.messages)
        response.append(
            ConversationResponse(
                id=conv.id,
                agent_id=conv.agent_id,
                title=conv.title,
                created_at=conv.created_at.isoformat(),
                message_count=message_count
            )
        )
    return response

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse], tags=["User Console - Conversations"])
def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    return conversation.messages

@router.delete("/conversations/{conversation_id}", tags=["User Console - Conversations"])
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    db.delete(conversation)
    db.commit()
    return {"deleted": True, "conversation_id": conversation_id}

@router.patch("/conversations/{conversation_id}", tags=["User Console - Conversations"])
def update_conversation(
    conversation_id: int,
    payload: UpdateConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    conversation.title = payload.title
    db.commit()
    db.refresh(conversation)
    return conversation

@router.post("/conversations/{conversation_id}/attachments", tags=["User Console - Conversations"])
async def upload_attachment(
    conversation_id: int,
    file: UploadFile = File(...),
    agent_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    raw = await file.read()
    doc_id = str(uuid.uuid4())
    doc = KnowledgeItem(
        id=doc_id,
        tenant_id=tenant_id,
        filename=file.filename,
        mime=file.content_type,
        size=len(raw),
        tags=["chat_upload", f"conversation_{conversation_id}"],
        checksum=hashlib.sha256(raw).hexdigest(),
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        text_content = extract_text(file, raw)
        vectorize_document(db, tenant_id, doc.id, text_content)
    except Exception as e:
        db.query(KnowledgeItem).filter(KnowledgeItem.id == doc.id).update({"status": "error", "error_reason": str(e)})
        db.commit()
        raise HTTPException(status_code=500, detail=f"Falha na vetorização: {e}")

    try:
        db.add(AgentDocument(agent_id=agent_id, document_id=doc.id))
        db.commit()
    except Exception:
        db.rollback()

    return {
        "ok": True,
        "document_id": doc.id,
        "filename": file.filename,
        "status": "vectorized"
    }
