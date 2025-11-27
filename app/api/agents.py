from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Agent, User
from app.core.config import settings
from app.core.security import get_current_user

router = APIRouter(prefix=f"{settings.API_V1_STR}/agents", tags=["agents"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AgentCreate(BaseModel):
    owner_id: int
    name: str
    purpose: str = ""
    temperature: float = 0.2

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    purpose: Optional[str] = None
    temperature: Optional[float] = None

def ensure_owner_or_admin(user: User, agent: Agent):
    if user.role not in ("ADMIN", "OWNER"):
        raise HTTPException(status_code=403, detail="forbidden")
    if user.role == "OWNER" and agent.owner_id != user.id:
        raise HTTPException(status_code=403, detail="forbidden")

@router.get("")
def list_agents(db: Session = Depends(get_db)):
    return db.query(Agent).all()

@router.post("")
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)):
    if not db.query(User).filter(User.id == payload.owner_id).first():
        raise HTTPException(400, "owner not found")
    a = Agent(**payload.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a

@router.put("/{agent_id}", response_model=dict)
def update_agent(agent_id: int, body: AgentUpdate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="not found")
    ensure_owner_or_admin(current, agent)
    if body.name is not None: agent.name = body.name
    if body.purpose is not None: agent.purpose = body.purpose
    if body.temperature is not None: agent.temperature = body.temperature
    db.commit(); db.refresh(agent)
    return {"ok": True, "id": agent.id}

@router.delete("/{agent_id}", response_model=dict, status_code=200)
def delete_agent(agent_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="not found")
    ensure_owner_or_admin(current, agent)
    db.delete(agent); db.commit()
    return {"ok": True}
