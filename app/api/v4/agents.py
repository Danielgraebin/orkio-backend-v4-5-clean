"""
ORKIO v4.0 - Rotas de Agentes
GET /api/v1/u/agents - Lista agentes do tenant
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from app.core.database import get_db
from app.models.models import Agent
from app.core.auth_v4 import get_current_user, CurrentUser

router = APIRouter()


class AgentResponse(BaseModel):
    id: int
    name: str
    system_prompt: str | None
    temperature: float
    
    class Config:
        from_attributes = True


@router.get("/agents", response_model=List[AgentResponse])
def list_agents(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista todos os agentes do tenant do usuário autenticado
    """
    agents = db.query(Agent).filter(
        Agent.tenant_id == current_user.tenant_id
    ).all()
    
    return agents

