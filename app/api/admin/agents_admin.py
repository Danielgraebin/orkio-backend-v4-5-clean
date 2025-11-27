from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Agent, User
from app.core.config import settings
from app.core.security import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix=f"{settings.API_V1_STR}/admin/agents", tags=["admin-agents"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    purpose: Optional[str] = None
    temperature: Optional[float] = None
    rag_enabled: Optional[bool] = None
    use_rag: Optional[bool] = None  # Alias for compatibility
    provider: Optional[str] = None  # openai, anthropic, google
    llm_model: Optional[str] = None  # model name
    model: Optional[str] = None  # Legacy alias for llm_model

def ensure_admin(user: User):
    """Ensure user has admin privileges"""
    if user.role not in ("ADMIN", "OWNER"):
        raise HTTPException(status_code=403, detail="Admin access required")

@router.get("")
def list_agents_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all agents (admin only)"""
    ensure_admin(current_user)
    agents = db.query(Agent).all()
    return agents

@router.put("/{agent_id}")
def update_agent_admin(
    agent_id: int,
    body: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update agent (admin only)"""
    ensure_admin(current_user)
    
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update fields
    if body.name is not None:
        agent.name = body.name
    if body.purpose is not None:
        agent.purpose = body.purpose
    if body.temperature is not None:
        agent.temperature = body.temperature
    
    # Handle RAG (both rag_enabled and use_rag for compatibility)
    if body.rag_enabled is not None:
        agent.use_rag = body.rag_enabled
    elif body.use_rag is not None:
        agent.use_rag = body.use_rag
    
    # Handle provider
    if body.provider is not None:
        agent.provider = body.provider
    
    # Handle llm_model (with legacy model alias)
    if body.llm_model is not None:
        agent.llm_model = body.llm_model
    elif body.model is not None:
        agent.llm_model = body.model
    
    db.commit()
    db.refresh(agent)
    
    logger.info(f"Agent #{agent_id} updated by user #{current_user.id}")
    
    return {
        "ok": True,
        "id": agent.id,
        "name": agent.name,
        "purpose": agent.purpose,
        "temperature": agent.temperature,
        "use_rag": agent.use_rag,
        "provider": agent.provider,
        "llm_model": agent.llm_model
    }

