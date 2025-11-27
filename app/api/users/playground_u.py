
# api/users/playground_u.py
# v4.5: Playground com RAG e multi-tenant
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, get_current_user_tenant
from app.models.models import Agent, User
from app.services.rag_service import search as rag_search
from app.services.llm_manager import chat_completion as llm_chat
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class PlaygroundRun(BaseModel):
    prompt: str
    agent_id: int

@router.post("/run", tags=["User Console - Playground"])
def playground_run(
    payload: PlaygroundRun,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    """
    Playground endpoint com RAG e multi-tenant.
    """
    agent = db.query(Agent).filter(
        Agent.id == payload.agent_id,
        Agent.tenant_id == tenant_id,
        Agent.enabled_for_users == True
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado ou não habilitado para este tenant.")
    
    start = time.time()
    ctx, hits = ([], 0)
    if agent.use_rag:
        ctx, hits = rag_search(db, tenant_id, agent.id, payload.prompt)
    
    msgs = [{"role": "system", "content": agent.purpose or "Você é um assistente prestativo."}]
    
    if ctx:
        msgs.append({"role": "system", "content": "Base de Conhecimento:\n" + "\n\n".join(ctx)})
    
    msgs.append({"role": "user", "content": payload.prompt})
    
    try:
        out = llm_chat(
            messages=msgs,
            model=agent.llm_model or "gpt-4.1-mini",
            temperature=agent.temperature or 0.7
        )
        
        ms = int((time.time() - start) * 1000)
        
        return {
            "status": "done",
            "output_text": out,
            "usage": {"tokens_used": 0, "requests": 1}, # Placeholder, será implementado na fase 5
            "latency_ms": ms
        }
    
    except Exception as e:
        logger.exception("Playground run failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health", tags=["User Console - Playground"])
def health():
    return {"ok": True}
