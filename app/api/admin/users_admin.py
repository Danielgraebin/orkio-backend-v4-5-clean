from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import User, Agent, UserAgent
from app.core.config import settings
from app.core.security import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix=f"{settings.API_V1_STR}/admin/users", tags=["admin-users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ensure_admin(user: User):
    """Ensure user has admin privileges"""
    if user.role not in ("ADMIN", "OWNER"):
        raise HTTPException(status_code=403, detail="Admin access required")

@router.get("/pending")
def list_pending_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List users awaiting approval (admin only)"""
    ensure_admin(current_user)
    
    users = db.query(User).filter(User.is_approved == False).all()
    
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "is_approved": u.is_approved,
            "created_at": u.created_at.isoformat() if hasattr(u, 'created_at') else None
        }
        for u in users
    ]

@router.get("")
def list_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all users (admin only)"""
    ensure_admin(current_user)
    
    users = db.query(User).all()
    
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "is_approved": u.is_approved,
            "created_at": u.created_at.isoformat() if hasattr(u, 'created_at') else None
        }
        for u in users
    ]

from pydantic import BaseModel
from typing import Literal

class ApproveUserRequest(BaseModel):
    role: Literal["USER", "ADMIN"] = "USER"

@router.post("/{user_id}/approve")
def approve_user(
    user_id: int,
    payload: ApproveUserRequest = ApproveUserRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve user and set role (admin only).
    POST /admin/users/{user_id}/approve
    Body: {"role": "USER" | "ADMIN"}
    """
    ensure_admin(current_user)
    
    # Apenas OWNER pode promover a ADMIN
    if payload.role == "ADMIN" and current_user.role != "OWNER":
        raise HTTPException(status_code=403, detail="Only OWNER can promote to ADMIN")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_approved:
        return {"ok": True, "message": "User already approved"}
    
    # Approve user and set role
    user.is_approved = True
    user.role = payload.role
    db.commit()
    
    logger.info(f"User #{user_id} ({user.email}) approved by admin #{current_user.id}")
    
    # Auto-bind default agents
    # Get all agents from owner_id=1 (default tenant)
    default_agents = db.query(Agent).filter(Agent.owner_id == 1).all()
    
    for agent in default_agents:
        # Check if binding already exists
        existing = db.query(UserAgent).filter(
            UserAgent.user_id == user_id,
            UserAgent.agent_id == agent.id
        ).first()
        
        if not existing:
            user_agent = UserAgent(user_id=user_id, agent_id=agent.id)
            db.add(user_agent)
    
    db.commit()
    
    logger.info(f"Auto-bound {len(default_agents)} agents to user #{user_id}")
    
    return {
        "ok": True,
        "user_id": user_id,
        "email": user.email,
        "is_approved": True,
        "agents_bound": len(default_agents)
    }

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete user (admin only)"""
    ensure_admin(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete user_agents bindings
    db.query(UserAgent).filter(UserAgent.user_id == user_id).delete()
    
    # Delete user
    db.delete(user)
    db.commit()
    
    logger.info(f"User #{user_id} deleted by admin #{current_user.id}")
    
    return {"ok": True}

