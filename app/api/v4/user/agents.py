"""
User Console - Agents endpoint
GET /api/v1/u/agents - List available agents for user
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_v4
from app.models.models import Agent, User

router = APIRouter()

@router.get("/agents")
def list_agents(
    current_user: User = Depends(get_current_user_v4),
    db: Session = Depends(get_db)
):
    """List all agents available for the user's tenant"""
    # Get tenant_id from token (stored in _tenant_id by get_current_user_v4)
    tenant_id = getattr(current_user, '_tenant_id', None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant_id in token")
    
    agents = db.query(Agent).filter(Agent.tenant_id == tenant_id).all()
    return [
        {
            "id": agent.id,
            "name": agent.name,
            "model": agent.model,
            "provider": agent.provider,
            "system_prompt": agent.system_prompt,
            "temperature": agent.temperature,
        }
        for agent in agents
    ]

