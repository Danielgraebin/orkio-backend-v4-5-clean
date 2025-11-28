"""
Rotas Admin v4 - Users
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.core.database import get_db
from app.models.models import User, Membership, Tenant
from app.core.auth_v4 import get_current_user, CurrentUser

router = APIRouter()


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    tenant_id: int
    tenant_name: str
    created_at: str
    
    class Config:
        from_attributes = True


class UpdateUserRoleRequest(BaseModel):
    role: str  # "OWNER", "ADMIN", "USER"


@router.get("/users", response_model=dict)
def list_users(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista todos os usuários do tenant atual.
    Apenas OWNER ou ADMIN podem acessar.
    """
    # Verificar permissão
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not membership or membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    
    # Buscar todos usuários do tenant
    memberships = db.query(Membership, User, Tenant).join(
        User, Membership.user_id == User.id
    ).join(
        Tenant, Membership.tenant_id == Tenant.id
    ).filter(
        Membership.tenant_id == current_user.tenant_id
    ).all()
    
    users = []
    for m, u, t in memberships:
        users.append({
            "id": u.id,
            "email": u.email,
            "role": m.role,
            "tenant_id": t.id,
            "tenant_name": t.name,
            "created_at": u.created_at.isoformat() if u.created_at else None
        })
    
    return {"users": users}


@router.patch("/users/{user_id}", response_model=dict)
def update_user_role(
    user_id: int,
    request: UpdateUserRoleRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atualiza o papel (role) de um usuário no tenant.
    Apenas OWNER, ADMIN ou SUPERADMIN podem executar.
    """
    # Verificar se current_user é OWNER, ADMIN ou SUPERADMIN
    current_membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not current_membership or current_membership.role not in ["OWNER", "ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden: Only OWNER, ADMIN or SUPERADMIN can change roles")
    
    # Buscar membership do usuário alvo
    target_membership = db.query(Membership).filter(
        Membership.user_id == user_id,
        Membership.tenant_id == current_user.tenant_id
    ).first()
    
    if not target_membership:
        raise HTTPException(status_code=404, detail="User not found in this tenant")
    
    # Validar role
    if request.role not in ["OWNER", "ADMIN", "USER", "SUPERADMIN"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Atualizar
    target_membership.role = request.role
    db.commit()
    db.refresh(target_membership)
    
    # Buscar user para retornar
    user = db.query(User).filter(User.id == user_id).first()
    
    return {
        "id": user.id,
        "email": user.email,
        "role": target_membership.role
    }

