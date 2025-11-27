_# api/users/chat_u.py
# v4.5: Chat com RAG e multi-tenant
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.deps import get_db, get_current_user, get_current_user_tenant
from app.models.models import Agent, User, Conversation, ConversationMessage
from app.services.rag_service import search as rag_search
from app.services.llm_manager import chat_completion as llm_chat
from typing import List, Literal, Optional
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    agent_id: int
    message: str
    conversation_id: Optional[int] = None
    history: List[ChatMessage] = []

@router.post("/chat", tags=["User Console - Chat"])
def user_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    """
    Chat endpoint com RAG e multi-tenant.
    """
    if not current_user.is_approved:
        raise HTTPException(status_code=403, detail="Acesso pendente de aprovação")

    agent = db.query(Agent).filter(
        Agent.id == payload.agent_id,
        Agent.tenant_id == tenant_id,  # Filtro por tenant
        Agent.enabled_for_users == True
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado ou não habilitado para este tenant.")

    context_blocks, hits = ([], 0)
    if agent.use_rag:
        context_blocks, hits = rag_search(db, tenant_id=tenant_id, agent_id=agent.id, query=payload.message)

    messages = [{"role": "system", "content": agent.purpose or "Você é um assistente prestativo."}]

    if context_blocks:
        ctx = "\n\n".join(context_blocks)
        messages.append({"role": "system", "content": f"Use os seguintes trechos da base de conhecimento quando relevante:\n{ctx}"})

    for msg in payload.history:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": payload.message})

    if agent.use_rag and hits == 0:
        return {
            "reply": "Não encontrei informações relevantes na base de conhecimento para responder com segurança. Deseja vincular documentos ao agente?",
            "circuit_breaker": True
        }

    conversation_id = payload.conversation_id
    if not conversation_id:
        new_conversation = Conversation(
            tenant_id=tenant_id,
            agent_id=agent.id,
            user_id=current_user.id,
            title=payload.message[:50] + "..." if len(payload.message) > 50 else payload.message
        )
        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)
        conversation_id = new_conversation.id

    if conversation_id:
        user_message = ConversationMessage(conversation_id=conversation_id, role='user', content=payload.message)
        db.add(user_message)
        db.commit()

    try:
        out = llm_chat(
            messages=messages,
            model=agent.llm_model or "gpt-4.1-mini",
            temperature=agent.temperature or 0.7
        )

        if conversation_id:
            assistant_message = ConversationMessage(conversation_id=conversation_id, role='assistant', content=out)
            db.add(assistant_message)
            db.commit()

        return {"reply": out, "conversation_id": conversation_id}

    except ValueError as e:
        logger.error(f"LLM client error: {e}")
        raise HTTPException(status_code=424, detail=f"LLM dependency failed: {str(e)}")

    except Exception as e:
        logger.exception("LLM server error or timeout")
        raise HTTPException(status_code=502, detail=f"LLM service unavailable: {str(e)}")
