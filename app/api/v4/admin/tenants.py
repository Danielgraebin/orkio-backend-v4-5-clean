"""
Admin endpoints for Tenant management (CRUD)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import Tenant, User
from app.core.auth_v4 import get_current_user
from app.core.audit import log_audit, AuditAction

router = APIRouter()


# ===== SCHEMAS =====

class TenantCreate(BaseModel):
    name: str
    slug: str
    default_provider: Optional[str] = None
    allowed_models: Optional[List[str]] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[bool] = None
    default_provider: Optional[str] = None
    allowed_models: Optional[List[str]] = None


class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool
    default_provider: Optional[str]
    allowed_models: Optional[List[str]]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class TenantDetailResponse(TenantResponse):
    user_count: int
    agent_count: int
    conversation_count: int


# ===== HELPER FUNCTIONS =====

def require_admin(user: User):
    """Ensure user has admin or superadmin role"""
    if user.role not in ["ADMIN", "OWNER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )


# ===== ENDPOINTS =====

@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant_data: TenantCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Create a new tenant (Admin only)
    """
    require_admin(user)
    
    # Check if slug already exists
    existing = db.query(Tenant).filter(Tenant.slug == tenant_data.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with slug '{tenant_data.slug}' already exists"
        )
    
    # Check if name already exists
    existing_name = db.query(Tenant).filter(Tenant.name == tenant_data.name).first()
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with name '{tenant_data.name}' already exists"
        )
    
    # Create tenant
    new_tenant = Tenant(
        name=tenant_data.name,
        slug=tenant_data.slug,
        is_active=True,
        default_provider=tenant_data.default_provider,
        allowed_models=tenant_data.allowed_models
    )
    
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)
    
    # Log audit
    log_audit(
        db=db,
        action=AuditAction.TENANT_CREATED,
        user_id=user.id,
        resource_type="tenant",
        resource_id=new_tenant.id,
        metadata={"tenant_name": new_tenant.name, "slug": new_tenant.slug},
        request=request
    )
    
    return new_tenant


@router.get("/tenants", response_model=List[TenantResponse])
def list_tenants(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    List all tenants (Admin only)
    """
    require_admin(user)
    
    tenants = db.query(Tenant).offset(skip).limit(limit).all()
    return tenants


@router.get("/tenants/{tenant_id}", response_model=TenantDetailResponse)
def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get tenant details with statistics (Admin only)
    """
    require_admin(user)
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Count related entities
    from app.models.models import Membership, Agent, Conversation
    
    user_count = db.query(Membership).filter(Membership.tenant_id == tenant_id).count()
    agent_count = db.query(Agent).filter(Agent.tenant_id == tenant_id).count()
    conversation_count = db.query(Conversation).filter(Conversation.tenant_id == tenant_id).count()
    
    return {
        **tenant.__dict__,
        "user_count": user_count,
        "agent_count": agent_count,
        "conversation_count": conversation_count
    }


@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Update tenant information (Admin only)
    """
    require_admin(user)
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Update fields if provided
    if tenant_data.name is not None:
        # Check if new name already exists
        existing = db.query(Tenant).filter(
            Tenant.name == tenant_data.name,
            Tenant.id != tenant_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant with name '{tenant_data.name}' already exists"
            )
        tenant.name = tenant_data.name
    
    if tenant_data.slug is not None:
        # Check if new slug already exists
        existing = db.query(Tenant).filter(
            Tenant.slug == tenant_data.slug,
            Tenant.id != tenant_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant with slug '{tenant_data.slug}' already exists"
            )
        tenant.slug = tenant_data.slug
    
    if tenant_data.is_active is not None:
        tenant.is_active = tenant_data.is_active
    
    if tenant_data.default_provider is not None:
        tenant.default_provider = tenant_data.default_provider
    
    if tenant_data.allowed_models is not None:
        tenant.allowed_models = tenant_data.allowed_models
    
    tenant.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(tenant)
    
    # Log audit
    changes = {}
    if tenant_data.name is not None:
        changes["name"] = tenant_data.name
    if tenant_data.slug is not None:
        changes["slug"] = tenant_data.slug
    if tenant_data.is_active is not None:
        action = AuditAction.TENANT_ACTIVATED if tenant_data.is_active else AuditAction.TENANT_DEACTIVATED
        changes["is_active"] = tenant_data.is_active
    else:
        action = AuditAction.TENANT_UPDATED
    
    log_audit(
        db=db,
        action=action,
        user_id=user.id,
        resource_type="tenant",
        resource_id=tenant.id,
        metadata={"tenant_name": tenant.name, "changes": changes},
        request=request
    )
    
    return tenant


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Delete (deactivate) a tenant (Admin only)
    Note: This sets is_active to False instead of actually deleting
    """
    require_admin(user)
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Soft delete: just deactivate
    tenant.is_active = False
    tenant.updated_at = datetime.utcnow()
    
    db.commit()
    
    return None
