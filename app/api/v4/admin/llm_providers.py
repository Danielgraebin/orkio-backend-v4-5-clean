from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.auth_v4 import get_current_user
from app.models.models import User, Membership
from cryptography.fernet import Fernet
import os

router = APIRouter()

# Encryption key for API keys (should be in environment variables)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
cipher = Fernet(ENCRYPTION_KEY)

# ===== SCHEMAS =====

class LLMProviderResponse(BaseModel):
    id: int
    name: str
    slug: str
    enabled: bool
    created_at: str
    has_api_key: bool = False  # Indica se o tenant tem API key configurada
    
    class Config:
        from_attributes = True

class LLMModelResponse(BaseModel):
    id: int
    provider_id: int
    name: str
    model_id: str
    enabled: bool
    default_temperature: float | None
    created_at: str
    has_api_key: bool = False  # Indica se o tenant tem API key configurada
    
    class Config:
        from_attributes = True

class APIKeyCreate(BaseModel):
    provider_id: int
    model_id: int | None = None
    api_key: str
    base_url: str | None = None

class APIKeyUpdate(BaseModel):
    api_key: str | None = None
    base_url: str | None = None

# ===== HELPER FUNCTIONS =====

def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key for storage"""
    return cipher.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key for usage"""
    return cipher.decrypt(encrypted_key.encode()).decode()

def check_admin_permission(current_user: User, db: Session):
    """Check if user has ADMIN or SUPERADMIN role"""
    # Use SQL puro para melhor performance
    query = text("""
        SELECT tenant_id, role 
        FROM memberships 
        WHERE user_id = :user_id
        LIMIT 1
    """)
    
    result = db.execute(query, {"user_id": current_user.user_id}).first()
    
    if not result or result[1] not in ["ADMIN", "SUPERADMIN", "OWNER"]:
        raise HTTPException(status_code=403, detail="Forbidden: Only ADMIN, SUPERADMIN or OWNER can manage LLM providers")
    
    # Retornar objeto com tenant_id e role
    class MembershipData:
        def __init__(self, tenant_id, role):
            self.tenant_id = tenant_id
            self.role = role
    
    return MembershipData(result[0], result[1])

# ===== PROVIDERS ENDPOINTS =====

@router.get("/llm/providers", response_model=List[LLMProviderResponse], tags=["admin-llm"])
def list_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all LLM providers.
    Only ADMIN, SUPERADMIN or OWNER can execute.
    """
    membership = check_admin_permission(current_user, db)
    
    # Query providers and check if tenant has API keys
    query = text("""
        SELECT 
            p.id,
            p.name,
            p.slug,
            p.enabled,
            p.created_at,
            CASE WHEN k.id IS NOT NULL THEN true ELSE false END as has_api_key
        FROM llm_providers p
        LEFT JOIN llm_api_keys k ON k.provider_id = p.id AND k.tenant_id = :tenant_id
        ORDER BY p.id
    """)
    
    result = db.execute(query, {"tenant_id": membership.tenant_id})
    providers = []
    for row in result:
        providers.append({
            "id": row[0],
            "name": row[1],
            "slug": row[2],
            "enabled": row[3],
            "created_at": str(row[4]),
            "has_api_key": row[5]
        })
    
    return providers

@router.get("/llm/providers/{provider_id}", response_model=LLMProviderResponse, tags=["admin-llm"])
def get_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific LLM provider.
    Only ADMIN, SUPERADMIN or OWNER can execute.
    """
    membership = check_admin_permission(current_user, db)
    
    query = text("""
        SELECT 
            p.id,
            p.name,
            p.slug,
            p.enabled,
            p.created_at,
            CASE WHEN k.id IS NOT NULL THEN true ELSE false END as has_api_key
        FROM llm_providers p
        LEFT JOIN llm_api_keys k ON k.provider_id = p.id AND k.tenant_id = :tenant_id
        WHERE p.id = :provider_id
    """)
    
    result = db.execute(query, {"tenant_id": membership.tenant_id, "provider_id": provider_id}).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return {
        "id": result[0],
        "name": result[1],
        "slug": result[2],
        "enabled": result[3],
        "created_at": str(result[4]),
        "has_api_key": result[5]
    }

# ===== MODELS ENDPOINTS =====

@router.get("/llm/models", response_model=List[LLMModelResponse], tags=["admin-llm"])
def list_models(
    provider_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all LLM models, optionally filtered by provider.
    Only ADMIN, SUPERADMIN or OWNER can execute.
    """
    membership = check_admin_permission(current_user, db)
    
    if provider_id:
        query = text("""
            SELECT 
                m.id,
                m.provider_id,
                m.name,
                m.model_id,
                m.enabled,
                m.default_temperature,
                m.created_at,
                CASE WHEN k.id IS NOT NULL THEN true ELSE false END as has_api_key
            FROM llm_models m
            LEFT JOIN llm_api_keys k ON k.model_id = m.id AND k.tenant_id = :tenant_id
            WHERE m.provider_id = :provider_id
            ORDER BY m.id
        """)
        result = db.execute(query, {"tenant_id": membership.tenant_id, "provider_id": provider_id})
    else:
        query = text("""
            SELECT 
                m.id,
                m.provider_id,
                m.name,
                m.model_id,
                m.enabled,
                m.default_temperature,
                m.created_at,
                CASE WHEN k.id IS NOT NULL THEN true ELSE false END as has_api_key
            FROM llm_models m
            LEFT JOIN llm_api_keys k ON k.model_id = m.id AND k.tenant_id = :tenant_id
            ORDER BY m.provider_id, m.id
        """)
        result = db.execute(query, {"tenant_id": membership.tenant_id})
    
    models = []
    for row in result:
        models.append({
            "id": row[0],
            "provider_id": row[1],
            "name": row[2],
            "model_id": row[3],
            "enabled": row[4],
            "default_temperature": row[5],
            "created_at": str(row[6]),
            "has_api_key": row[7]
        })
    
    return models

@router.get("/llm/models/{model_id}", response_model=LLMModelResponse, tags=["admin-llm"])
def get_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific LLM model.
    Only ADMIN, SUPERADMIN or OWNER can execute.
    """
    membership = check_admin_permission(current_user, db)
    
    query = text("""
        SELECT 
            m.id,
            m.provider_id,
            m.name,
            m.model_id,
            m.enabled,
            m.default_temperature,
            m.created_at,
            CASE WHEN k.id IS NOT NULL THEN true ELSE false END as has_api_key
        FROM llm_models m
        LEFT JOIN llm_api_keys k ON k.model_id = m.id AND k.tenant_id = :tenant_id
        WHERE m.id = :model_id
    """)
    
    result = db.execute(query, {"tenant_id": membership.tenant_id, "model_id": model_id}).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return {
        "id": result[0],
        "provider_id": result[1],
        "name": result[2],
        "model_id": result[3],
        "enabled": result[4],
        "default_temperature": result[5],
        "created_at": str(result[6]),
        "has_api_key": result[7]
    }

# ===== API KEYS ENDPOINTS =====

@router.post("/llm/api-keys", tags=["admin-llm"])
def create_api_key(
    api_key_data: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create or update an API key for a provider/model.
    Only ADMIN, SUPERADMIN or OWNER can execute.
    """
    membership = check_admin_permission(current_user, db)
    
    # Encrypt API key
    encrypted_key = encrypt_api_key(api_key_data.api_key)
    
    # Check if API key already exists
    query = text("""
        SELECT id FROM llm_api_keys
        WHERE tenant_id = :tenant_id 
        AND provider_id = :provider_id 
        AND (model_id = :model_id OR (model_id IS NULL AND :model_id IS NULL))
    """)
    
    existing = db.execute(query, {
        "tenant_id": membership.tenant_id,
        "provider_id": api_key_data.provider_id,
        "model_id": api_key_data.model_id
    }).first()
    
    if existing:
        # Update existing key
        update_query = text("""
            UPDATE llm_api_keys
            SET encrypted_api_key = :encrypted_key,
                base_url = :base_url,
                updated_at = NOW()
            WHERE id = :id
        """)
        db.execute(update_query, {
            "id": existing[0],
            "encrypted_key": encrypted_key,
            "base_url": api_key_data.base_url
        })
    else:
        # Insert new key
        insert_query = text("""
            INSERT INTO llm_api_keys (tenant_id, provider_id, model_id, encrypted_api_key, base_url)
            VALUES (:tenant_id, :provider_id, :model_id, :encrypted_key, :base_url)
        """)
        db.execute(insert_query, {
            "tenant_id": membership.tenant_id,
            "provider_id": api_key_data.provider_id,
            "model_id": api_key_data.model_id,
            "encrypted_key": encrypted_key,
            "base_url": api_key_data.base_url
        })
    
    db.commit()
    
    return {"message": "API key saved successfully"}

@router.delete("/llm/api-keys/{provider_id}", tags=["admin-llm"])
def delete_api_key(
    provider_id: int,
    model_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an API key for a provider/model.
    Only ADMIN, SUPERADMIN or OWNER can execute.
    """
    membership = check_admin_permission(current_user, db)
    
    query = text("""
        DELETE FROM llm_api_keys
        WHERE tenant_id = :tenant_id 
        AND provider_id = :provider_id 
        AND (model_id = :model_id OR (model_id IS NULL AND :model_id IS NULL))
    """)
    
    db.execute(query, {
        "tenant_id": membership.tenant_id,
        "provider_id": provider_id,
        "model_id": model_id
    })
    
    db.commit()
    
    return {"message": "API key deleted successfully"}
