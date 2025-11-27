"""
ORKIO v4.0 - Rotas de Conversas
GET /api/v1/u/conversations - Lista conversas do usuário
POST /api/v1/u/conversations - Cria nova conversa
GET /api/v1/u/conversations/{id}/messages - Histórico de mensagens
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.models.models import Conversation, ConversationMessage, Agent
from app.core.auth_v4 import get_current_user, CurrentUser

router = APIRouter()


# ===== SCHEMAS =====

class CreateConversationRequest(BaseModel):
    agent_id: int
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    agent_id: int
    agent_name: str
    title: str | None
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ===== ROTAS =====

@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista todas as conversas do tenant do usuário
    """
    conversations = db.query(Conversation).filter(
        Conversation.tenant_id == current_user.tenant_id
    ).order_by(Conversation.created_at.desc()).all()
    
    # Enriquecer com nome do agente
    result = []
    for conv in conversations:
        agent = db.query(Agent).filter(Agent.id == conv.agent_id).first()
        result.append({
            "id": conv.id,
            "agent_id": conv.agent_id,
            "agent_name": agent.name if agent else "Unknown",
            "title": conv.title,
            "created_at": conv.created_at
        })
    
    return result


@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    req: CreateConversationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cria nova conversa com um agente
    """
    # Verificar se agente existe e pertence ao tenant
    agent = db.query(Agent).filter(
        Agent.id == req.agent_id,
        Agent.tenant_id == current_user.tenant_id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agente não encontrado"
        )
    
    # Criar conversa
    conversation = Conversation(
        tenant_id=current_user.tenant_id,
        agent_id=req.agent_id,
        title=req.title or f"Conversa com {agent.name}"
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    return {
        "id": conversation.id,
        "agent_id": conversation.agent_id,
        "agent_name": agent.name,
        "title": conversation.title,
        "created_at": conversation.created_at
    }


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
def get_conversation_messages(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna histórico de mensagens de uma conversa
    """
    # Verificar se conversa existe e pertence ao tenant
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.tenant_id == current_user.tenant_id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Buscar mensagens
    messages = db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id == conversation_id
    ).order_by(ConversationMessage.created_at.asc()).all()
    
    return messages

