"""
Admin endpoints for Audit Logs
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.models import User
from app.core.auth_v4 import get_current_user

router = APIRouter()


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    user_email: Optional[str]
    tenant_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    metadata: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


def require_admin(user: User):
    """Check if user has admin privileges"""
    if user.role not in ["ADMIN", "OWNER", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/audit-logs", response_model=dict)
def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    List audit logs with filtering (Admin only)
    """
    require_admin(user)
    
    query = db.query(AuditLog)
    
    # Apply filters
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if tenant_id:
        query = query.filter(AuditLog.tenant_id == tenant_id)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    
    # Order by most recent first
    query = query.order_by(AuditLog.created_at.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    logs = query.offset(skip).limit(limit).all()
    
    # Format response with user email
    logs_list = []
    for log in logs:
        log_dict = {
            "id": log.id,
            "user_id": log.user_id,
            "user_email": log.user.email if log.user else None,
            "tenant_id": log.tenant_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "extra_data": log.extra_data,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat()
        }
        logs_list.append(log_dict)
    
    return {
        "logs": logs_list,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/audit-logs/actions", response_model=dict)
def list_audit_actions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    List all distinct audit actions (Admin only)
    """
    require_admin(user)
    
    actions = db.query(AuditLog.action).distinct().all()
    action_list = [action[0] for action in actions]
    
    return {"actions": action_list}
