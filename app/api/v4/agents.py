"""
ORKIO v4.0 - Rotas de Agentes (User)
GET /api/v1/u/agents - Lista agentes do tenant
POST /api/v1/u/agents - Cria novo agente
PATCH /api/v1/u/agents/{agent_id} - Atualiza agente
DELETE /api/v1/u/agents/{agent_id} - Deleta agente
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import get_db
from app.models.models import Agent
from app.core.auth_v4 import get_current_user, CurrentUser

router = APIRouter()


class AgentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    provider: str
    model: str
    temperature: float
    max_tokens: Optional[int] = None
    is_active: bool = True
    created_at: str
    
    class Config:
        from_attributes = True


class CreateAgentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    provider_id: int
    model_id: int
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    is_active: bool = True


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    provider_id: Optional[int] = None
    model_id: Optional[int] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    is_active: Optional[bool] = None


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
    
    # Convert to response format
    result = []
    for agent in agents:
        result.append({
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "system_prompt": agent.system_prompt,
            "provider": agent.provider or "openai",
            "model": agent.model or "gpt-4",
            "temperature": agent.temperature or 0.7,
            "max_tokens": agent.max_tokens,
            "is_active": agent.is_active if hasattr(agent, 'is_active') else True,
            "created_at": agent.created_at.isoformat() if agent.created_at else "",
        })
    
    return result


@router.post("/agents", response_model=AgentResponse)
def create_agent(
    request: CreateAgentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cria um novo agente para o tenant do usuário
    """
    # Get provider and model names from IDs
    from app.models.models import LLMProvider, LLMModel
    
    provider = db.query(LLMProvider).filter(LLMProvider.id == request.provider_id).first()
    model = db.query(LLMModel).filter(LLMModel.id == request.model_id).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Create agent
    agent = Agent(
        tenant_id=current_user.tenant_id,
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        provider=provider.slug,
        model=model.model_id,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    
    # Add is_active if the column exists
    if hasattr(Agent, 'is_active'):
        agent.is_active = request.is_active
    
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "provider": agent.provider,
        "model": agent.model,
        "temperature": agent.temperature,
        "max_tokens": agent.max_tokens,
        "is_active": agent.is_active if hasattr(agent, 'is_active') else True,
        "created_at": agent.created_at.isoformat() if agent.created_at else "",
    }


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: int,
    request: UpdateAgentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atualiza um agente do tenant do usuário
    """
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.tenant_id == current_user.tenant_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update fields
    if request.name is not None:
        agent.name = request.name
    if request.description is not None:
        agent.description = request.description
    if request.system_prompt is not None:
        agent.system_prompt = request.system_prompt
    if request.temperature is not None:
        agent.temperature = request.temperature
    if request.max_tokens is not None:
        agent.max_tokens = request.max_tokens
    if request.is_active is not None and hasattr(agent, 'is_active'):
        agent.is_active = request.is_active
    
    # Update provider and model if provided
    if request.provider_id is not None or request.model_id is not None:
        from app.models.models import LLMProvider, LLMModel
        
        if request.provider_id:
            provider = db.query(LLMProvider).filter(LLMProvider.id == request.provider_id).first()
            if provider:
                agent.provider = provider.slug
        
        if request.model_id:
            model = db.query(LLMModel).filter(LLMModel.id == request.model_id).first()
            if model:
                agent.model = model.model_id
    
    db.commit()
    db.refresh(agent)
    
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "provider": agent.provider,
        "model": agent.model,
        "temperature": agent.temperature,
        "max_tokens": agent.max_tokens,
        "is_active": agent.is_active if hasattr(agent, 'is_active') else True,
        "created_at": agent.created_at.isoformat() if agent.created_at else "",
    }


@router.delete("/agents/{agent_id}")
def delete_agent(
    agent_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deleta um agente do tenant do usuário
    """
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.tenant_id == current_user.tenant_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    db.delete(agent)
    db.commit()
    
    return {"message": "Agent deleted successfully"}
