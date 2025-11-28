"""
Rotas Admin v4 - User Approval
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models.models import User, Membership
from app.core.auth_v4 import get_current_user, CurrentUser
from app.core.audit import log_audit, AuditAction

router = APIRouter()


class UserResponse(BaseModel):
    id: int
    email: str
    status: str
    created_at: str
    
    class Config:
        from_attributes = True


@router.get("/users/pending", response_model=dict)
def list_pending_users(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista usuários pendentes de aprovação.
    """
    # Verificar permissão
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not membership or membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    
    # Buscar usuários pendentes
    users = db.query(User).filter(
        User.status == "PENDING"
    ).all()
    
    users_list = []
    for user in users:
        users_list.append({
            "id": user.id,
            "email": user.email,
            "status": user.status,
            "created_at": user.created_at.isoformat() if user.created_at else None
        })
    
    return {"users": users_list}


@router.post("/users/{user_id}/approve", response_model=dict)
def approve_user(
    user_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Aprova um usuário pendente.
    """
    # Verificar permissão
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not membership or membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    
    # Buscar usuário
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.status != "PENDING":
        raise HTTPException(status_code=400, detail="User is not pending approval")
    
    # Aprovar usuário
    user.status = "APPROVED"
    user.is_approved = True
    db.commit()
    
    # Log audit
    log_audit(
        db=db,
        action=AuditAction.USER_APPROVED,
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="user",
        resource_id=user.id,
        metadata={"approved_user_email": user.email},
        request=request
    )
    
    return {
        "message": "User approved successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "status": user.status
        }
    }


@router.post("/users/{user_id}/reject", response_model=dict)
def reject_user(
    user_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rejeita um usuário pendente.
    """
    # Verificar permissão
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not membership or membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    
    # Buscar usuário
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.status != "PENDING":
        raise HTTPException(status_code=400, detail="User is not pending approval")
    
    # Rejeitar usuário (marcar como REJECTED ou deletar)
    user.status = "REJECTED"
    db.commit()
    
    # Log audit
    log_audit(
        db=db,
        action=AuditAction.USER_REJECTED,
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="user",
        resource_id=user.id,
        metadata={"rejected_user_email": user.email},
        request=request
    )
    
    # Opcional: deletar usuário rejeitado
    # db.delete(user)
    # db.commit()
    
    return {
        "message": "User rejected successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "status": user.status
        }
    }

