
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, get_current_user_tenant
from app.models.models import Agent, User
from typing import List

router = APIRouter()

@router.get("/agents", tags=["User Console - Agents"])
def list_agents_for_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    """
    Lista todos os agentes para o tenant do usuário atual.
    Usado pelo User Console para popular dropdowns de seleção de agentes.
    """
    agents = db.query(Agent).filter(
        Agent.tenant_id == tenant_id,
        Agent.enabled_for_users == True
    ).all()

    return [
        {
            "id": a.id,
            "name": a.name,
            "purpose": a.purpose,
            "temperature": a.temperature,
            "use_rag": a.use_rag,
            "has_rag": a.use_rag
        }
        for a in agents
    ]
