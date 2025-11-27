
"""
Rotas Admin v4.5 - Agent Links (Orchestration) com Multi-Tenant
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json

from app.core.deps import get_db, get_current_user, get_current_user_tenant
from app.models.models import AgentLink, Agent, User

router = APIRouter()

class AgentLinkCreate(BaseModel):
    from_agent_id: int
    to_agent_id: int
    trigger_keywords: List[str]
    priority: int = 0

class AgentLinkResponse(BaseModel):
    id: int
    from_agent_id: int
    from_agent_name: str
    to_agent_id: int
    to_agent_name: str
    trigger_keywords: List[str]
    priority: int
    active: bool
    created_at: str

@router.get("/agent-links", response_model=List[AgentLinkResponse], tags=["Admin - Agent Links"])
def list_agent_links(
    agent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    query = db.query(AgentLink).filter(AgentLink.tenant_id == tenant_id)
    if agent_id:
        query = query.filter(
            (AgentLink.from_agent_id == agent_id) | (AgentLink.to_agent_id == agent_id)
        )
    
    links = query.all()
    response = []
    for link in links:
        from_agent = db.query(Agent).get(link.from_agent_id)
        to_agent = db.query(Agent).get(link.to_agent_id)
        response.append(AgentLinkResponse(
            id=link.id,
            from_agent_id=link.from_agent_id,
            from_agent_name=from_agent.name if from_agent else "N/A",
            to_agent_id=link.to_agent_id,
            to_agent_name=to_agent.name if to_agent else "N/A",
            trigger_keywords=json.loads(link.trigger_keywords) if link.trigger_keywords else [],
            priority=link.priority,
            active=link.active,
            created_at=link.created_at.isoformat()
        ))
    return response

@router.post("/agent-links", response_model=AgentLinkResponse, status_code=201, tags=["Admin - Agent Links"])
def create_agent_link(
    link_data: AgentLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    from_agent = db.query(Agent).filter(Agent.id == link_data.from_agent_id, Agent.tenant_id == tenant_id).first()
    to_agent = db.query(Agent).filter(Agent.id == link_data.to_agent_id, Agent.tenant_id == tenant_id).first()

    if not from_agent or not to_agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado neste tenant.")

    if link_data.from_agent_id == link_data.to_agent_id:
        raise HTTPException(status_code=400, detail="Não é possível criar um link para o mesmo agente.")

    link = AgentLink(
        tenant_id=tenant_id,
        from_agent_id=link_data.from_agent_id,
        to_agent_id=link_data.to_agent_id,
        trigger_keywords=json.dumps(link_data.trigger_keywords),
        priority=link_data.priority,
        active=True
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return AgentLinkResponse(
        id=link.id,
        from_agent_id=link.from_agent_id,
        from_agent_name=from_agent.name,
        to_agent_id=link.to_agent_id,
        to_agent_name=to_agent.name,
        trigger_keywords=link_data.trigger_keywords,
        priority=link.priority,
        active=link.active,
        created_at=link.created_at.isoformat()
    )

@router.delete("/agent-links/{link_id}", status_code=204, tags=["Admin - Agent Links"])
def delete_agent_link(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    link = db.query(AgentLink).filter(AgentLink.id == link_id, AgentLink.tenant_id == tenant_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link não encontrado.")
    db.delete(link)
    db.commit()

@router.patch("/agent-links/{link_id}/toggle", response_model=dict, tags=["Admin - Agent Links"])
def toggle_agent_link(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant)
):
    link = db.query(AgentLink).filter(AgentLink.id == link_id, AgentLink.tenant_id == tenant_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link não encontrado.")
    link.active = not link.active
    db.commit()
    return {"id": link.id, "active": link.active}
