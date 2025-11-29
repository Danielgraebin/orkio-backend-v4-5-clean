"""
Audit logging utilities
"""
from sqlalchemy.orm import Session
from fastapi import Request
from typing import Optional, Dict, Any
from app.models.audit_log import AuditLog


def log_audit(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    extra_data: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """
    Log an audit event
    
    Args:
        db: Database session
        action: Action performed (e.g., "user.approved", "tenant.created")
        user_id: ID of the user performing the action
        tenant_id: ID of the tenant affected
        resource_type: Type of resource (e.g., "user", "agent", "tenant")
        resource_id: ID of the resource affected
        extra_data: Additional metadata as JSON
        request: FastAPI request object to extract IP and user agent
    """
    ip_address = None
    user_agent = None
    
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
    
    audit_log = AuditLog(
        user_id=user_id,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        extra_data=extra_data,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(audit_log)
    db.commit()
    
    return audit_log


# Audit action constants
class AuditAction:
    # User actions
    USER_APPROVED = "user.approved"
    USER_REJECTED = "user.rejected"
    USER_ROLE_CHANGED = "user.role_changed"
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"
    
    # Tenant actions
    TENANT_CREATED = "tenant.created"
    TENANT_UPDATED = "tenant.updated"
    TENANT_ACTIVATED = "tenant.activated"
    TENANT_DEACTIVATED = "tenant.deactivated"
    TENANT_DELETED = "tenant.deleted"
    
    # Agent actions
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"
    
    # Auth actions
    PASSWORD_RESET_REQUESTED = "auth.password_reset_requested"
    PASSWORD_RESET_COMPLETED = "auth.password_reset_completed"
    LOGIN_SUCCESS = "auth.login_success"
    LOGIN_FAILED = "auth.login_failed"
    
    # LLM actions
    LLM_PROVIDER_TOGGLED = "llm.provider_toggled"
    LLM_MODEL_TOGGLED = "llm.model_toggled"
