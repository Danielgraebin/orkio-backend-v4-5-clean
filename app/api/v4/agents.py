"""
ORKIO v4.0 - Rotas de Agentes (User)
GET /api/v1/u/agents - Lista agentes do tenant
POST /api/v1/u/agents - Cria novo agente
PATCH /api/v1/u/agents/{agent_id} - Atualiza agente
DELETE /api/v1/u/agents/{agent_id} - Deleta agente
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, ValidationError
from typing import List, Optional
from app.core.database import get_db
from app.models.models import Agent
from app.core.auth_v4 import get_current_user, CurrentUser
import json

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
            "description": None,  # Column doesn't exist in DB
            "system_prompt": agent.system_prompt,
            "provider": agent.provider or "openai",
            "model": agent.model or "gpt-4",
            "temperature": agent.temperature or 0.7,
            "max_tokens": None,  # Column doesn't exist in DB
            "is_active": True,  # Column doesn't exist in DB, default to True
            "created_at": agent.created_at.isoformat() if agent.created_at else "",
        })
    
    return result


@router.post("/agents", response_model=AgentResponse)
async def create_agent(
    http_request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cria um novo agente para o tenant do usuário
    """
    # DEBUG: Log raw request body
    try:
        body = await http_request.json()
        print(f"[DEBUG CREATE_AGENT] Raw body: {json.dumps(body, indent=2)}")
        print(f"[DEBUG CREATE_AGENT] Current user: user_id={current_user.user_id}, tenant_id={current_user.tenant_id}, role={current_user.role}")
        request = CreateAgentRequest(**body)
        print(f"[DEBUG CREATE_AGENT] Validated request: {request.dict()}")
    except ValidationError as e:
        print(f"[DEBUG CREATE_AGENT] Validation error: {e.json()}")
        raise HTTPException(status_code=422, detail=e.errors())
    except Exception as e:
        print(f"[DEBUG CREATE_AGENT] Unexpected error: {str(e)}")
        raise
    
    # Get provider and model names from IDs using SQL
    from sqlalchemy import text
    
    provider_result = db.execute(text("""
        SELECT id, slug FROM llm_providers WHERE id = :provider_id
    """), {"provider_id": request.provider_id}).first()
    
    model_result = db.execute(text("""
        SELECT id, model_id FROM llm_models WHERE id = :model_id
    """), {"model_id": request.model_id}).first()
    
    if not provider_result:
        print(f"[DEBUG CREATE_AGENT] Provider not found: provider_id={request.provider_id}")
        raise HTTPException(status_code=404, detail="Provider not found")
    if not model_result:
        print(f"[DEBUG CREATE_AGENT] Model not found: model_id={request.model_id}")
        raise HTTPException(status_code=404, detail="Model not found")
    
    provider_slug = provider_result[1]
    model_id_str = model_result[1]
    print(f"[DEBUG CREATE_AGENT] Found provider: {provider_slug}, model: {model_id_str}")
    
    # Create agent (only use columns that exist in DB)
    print(f"[DEBUG CREATE_AGENT] Creating agent with: tenant_id={current_user.tenant_id}, name={request.name}, provider={provider_slug}, model={model_id_str}, temperature={request.temperature}")
    agent = Agent(
        tenant_id=current_user.tenant_id,
        name=request.name,
        # description - column doesn't exist
        system_prompt=request.system_prompt,
        provider=provider_slug,
        model=model_id_str,
        temperature=request.temperature,
        # max_tokens - column doesn't exist
        # is_active - column doesn't exist
    )
    
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    return {
        "id": agent.id,
        "name": agent.name,
        "description": None,  # Column doesn't exist
        "system_prompt": agent.system_prompt,
        "provider": agent.provider,
        "model": agent.model,
        "temperature": agent.temperature,
        "max_tokens": None,  # Column doesn't exist
        "is_active": True,  # Column doesn't exist, default to True
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
    
    # Update fields (only columns that exist in DB)
    if request.name is not None:
        agent.name = request.name
    # description - column doesn't exist, skip
    if request.system_prompt is not None:
        agent.system_prompt = request.system_prompt
    if request.temperature is not None:
        agent.temperature = request.temperature
    # max_tokens - column doesn't exist, skip
    # is_active - column doesn't exist, skip
    
    # Update provider and model if provided
    if request.provider_id is not None or request.model_id is not None:
        from sqlalchemy import text
        
        if request.provider_id:
            provider_result = db.execute(text("""
                SELECT id, slug FROM llm_providers WHERE id = :provider_id
            """), {"provider_id": request.provider_id}).first()
            if provider_result:
                agent.provider = provider_result[1]
        
        if request.model_id:
            model_result = db.execute(text("""
                SELECT id, model_id FROM llm_models WHERE id = :model_id
            """), {"model_id": request.model_id}).first()
            if model_result:
                agent.model = model_result[1]
    
    db.commit()
    db.refresh(agent)
    
    return {
        "id": agent.id,
        "name": agent.name,
        "description": None,  # Column doesn't exist
        "system_prompt": agent.system_prompt,
        "provider": agent.provider,
        "model": agent.model,
        "temperature": agent.temperature,
        "max_tokens": None,  # Column doesn't exist
        "is_active": True,  # Column doesn't exist, default to True
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
