from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import AgentLink
from app.core.config import settings
from app.core.security import get_current_user
from app.models.models import User

router = APIRouter(prefix=f"{settings.API_V1_STR}/links", tags=["links"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class LinkCreate(BaseModel):
    source_agent_id: int
    target_agent_id: int
    trigger: str = "on_result"
    action: str = "invoke"
    autonomy: str = "auto_safe"
    max_depth: int = 2
    enabled: bool = True
    filter_json: str = "{}"

class LinkUpdate(BaseModel):
    source_agent_id: Optional[int] = None
    target_agent_id: Optional[int] = None
    trigger: Optional[str] = None
    action: Optional[str] = None
    autonomy: Optional[str] = None
    max_depth: Optional[int] = None
    enabled: Optional[bool] = None
    filter_json: Optional[str] = None

@router.get("")
def list_links(db: Session = Depends(get_db)):
    return db.query(AgentLink).all()

@router.post("")
def create_link(payload: LinkCreate, db: Session = Depends(get_db)):
    link = AgentLink(**payload.model_dump())
    db.add(link)
    db.commit()
    db.refresh(link)
    return link

@router.put("/{link_id}", response_model=dict)
def update_link(link_id: int, body: LinkUpdate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    link = db.query(AgentLink).filter(AgentLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="not found")
    if body.source_agent_id is not None: link.source_agent_id = body.source_agent_id
    if body.target_agent_id is not None: link.target_agent_id = body.target_agent_id
    if body.trigger is not None: link.trigger = body.trigger
    if body.action is not None: link.action = body.action
    if body.autonomy is not None: link.autonomy = body.autonomy
    if body.max_depth is not None: link.max_depth = body.max_depth
    if body.enabled is not None: link.enabled = body.enabled
    if body.filter_json is not None: link.filter_json = body.filter_json
    db.commit(); db.refresh(link)
    return {"ok": True, "id": link.id}

@router.delete("/{link_id}", response_model=dict, status_code=200)
def delete_link(link_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    link = db.query(AgentLink).filter(AgentLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(link); db.commit()
    return {"ok": True}
