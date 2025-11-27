"""
Rotas Admin v4 - Agents
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.core.database import get_db
from app.models.models import Agent, Membership
from app.core.auth_v4 import get_current_user, CurrentUser

router = APIRouter()


class AgentResponse(BaseModel):
    id: int
    name: str
    system_prompt: str | None
    provider: str
    model: str
    temperature: float
    created_at: str
    
    class Config:
        from_attributes = True


class CreateAgentRequest(BaseModel):
    name: str
    system_prompt: str | None = None
    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    temperature: float = 0.7


class UpdateAgentRequest(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None


@router.get("/agents", response_model=dict)
def list_agents(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista todos agentes do tenant atual.
    """
    # Verificar permissão (ADMIN ou OWNER)
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not membership or membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    
    # Buscar agentes do tenant
    agents = db.query(Agent).filter(
        Agent.tenant_id == current_user.tenant_id
    ).all()
    
    agents_list = []
    for agent in agents:
        agents_list.append({
            "id": agent.id,
            "name": agent.name,
            "system_prompt": agent.system_prompt,
            "provider": agent.provider,
            "model": agent.model,
            "temperature": agent.temperature,
            "created_at": agent.created_at.isoformat() if agent.created_at else None
        })
    
    return {"agents": agents_list}


@router.post("/agents", response_model=dict, status_code=201)
def create_agent(
    request: CreateAgentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cria um novo agente no tenant.
    """
    # Verificar permissão
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not membership or membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    
    # Criar agente
    agent = Agent(
        tenant_id=current_user.tenant_id,
        name=request.name,
        system_prompt=request.system_prompt,
        provider=request.provider,
        model=request.model,
        temperature=request.temperature
    )
    
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    return {
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "system_prompt": agent.system_prompt,
            "provider": agent.provider,
            "model": agent.model,
            "temperature": agent.temperature,
            "created_at": agent.created_at.isoformat() if agent.created_at else None
        }
    }


@router.patch("/agents/{agent_id}", response_model=dict)
def update_agent(
    agent_id: int,
    request: UpdateAgentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atualiza um agente existente.
    """
    # Verificar permissão
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not membership or membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    
    # Buscar agente
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.tenant_id == current_user.tenant_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Atualizar campos
    if request.name is not None:
        agent.name = request.name
    if request.system_prompt is not None:
        agent.system_prompt = request.system_prompt
    if request.provider is not None:
        agent.provider = request.provider
    if request.model is not None:
        agent.model = request.model
    if request.temperature is not None:
        agent.temperature = request.temperature
    
    db.commit()
    db.refresh(agent)
    
    return {
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "system_prompt": agent.system_prompt,
            "provider": agent.provider,
            "model": agent.model,
            "temperature": agent.temperature,
            "created_at": agent.created_at.isoformat() if agent.created_at else None
        }
    }


@router.delete("/agents/{agent_id}", status_code=204)
def delete_agent(
    agent_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove um agente (soft delete).
    """
    # Verificar permissão
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not membership or membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    
    # Buscar agente
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.tenant_id == current_user.tenant_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Deletar
    db.delete(agent)
    db.commit()
    
    return None

