from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.auth_v4 import get_current_user
from app.models.models import LLMProvider, LLMModel, User, Membership
from cryptography.fernet import Fernet
import os

router = APIRouter()

# Encryption key for API keys (should be in environment variables)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
cipher = Fernet(ENCRYPTION_KEY)

# ===== SCHEMAS =====

class LLMProviderCreate(BaseModel):
    name: str
    provider_type: str  # openai, anthropic, google, manus
    api_key: str | None = None
    api_base_url: str | None = None
    is_active: bool = True

class LLMProviderUpdate(BaseModel):
    name: str | None = None
    api_key: str | None = None
    api_base_url: str | None = None
    is_active: bool | None = None

class LLMProviderResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    provider_type: str
    api_base_url: str | None
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True

class LLMModelCreate(BaseModel):
    provider_id: int
    name: str
    model_id: str
    max_tokens: int | None = None
    cost_per_1k_input_tokens: float | None = None
    cost_per_1k_output_tokens: float | None = None
    is_active: bool = True

class LLMModelUpdate(BaseModel):
    name: str | None = None
    model_id: str | None = None
    max_tokens: int | None = None
    cost_per_1k_input_tokens: float | None = None
    cost_per_1k_output_tokens: float | None = None
    is_active: bool | None = None

class LLMModelResponse(BaseModel):
    id: int
    provider_id: int
    name: str
    model_id: str
    max_tokens: int | None
    cost_per_1k_input_tokens: float | None
    cost_per_1k_output_tokens: float | None
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True

# ===== HELPER FUNCTIONS =====

def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key for storage"""
    return cipher.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key for usage"""
    return cipher.decrypt(encrypted_key.encode()).decode()

def check_admin_permission(current_user: User, db: Session):
    """Check if user has ADMIN or SUPERADMIN role"""
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id
    ).first()
    
    if not membership or membership.role not in ["ADMIN", "SUPERADMIN", "OWNER"]:
        raise HTTPException(status_code=403, detail="Forbidden: Only ADMIN, SUPERADMIN or OWNER can manage LLM providers")
    
    return membership

# ===== PROVIDERS ENDPOINTS =====

@router.post("/llm/providers", response_model=LLMProviderResponse, tags=["admin-llm"])
def create_provider(
    provider_data: LLMProviderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new LLM provider.
    Only ADMIN, SUPERADMIN or OWNER can execute.
    """
    membership = check_admin_permission(current_user, db)
    
    # Encrypt API key if provided
    encrypted_key = None
    if provider_data.api_key:
        encrypted_key = encrypt_api_key(provider_data.api_key)
    
    provider = LLMProvider(
        tenant_id=membership.tenant_id,
        name=provider_data.name,
        provider_type=provider_data.provider_type,
        api_key_encrypted=encrypted_key,
        api_base_url=provider_data.api_base_url,
        is_active=provider_data.is_active
    )
    
    db.add(provider)
    db.commit()
    db.refresh(provider)
    
    return provider

@router.get("/llm/providers", response_model=List[LLMProviderResponse], tags=["admin-llm"])
def list_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all LLM providers for the current tenant.
    Only ADMIN, SUPERADMIN or OWNER can execute.
    """
    membership = check_admin_permission(current_user, db)
    
    providers = db.query(LLMProvider).filter(
        LLMProvider.tenant_id == membership.tenant_id
    ).all()
    
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
    
    provider = db.query(LLMProvider).filter(
        LLMProvider.id == provider_id,
        LLMProvider.tenant_id == membership.tenant_id
    ).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return provider

@router.patch("/llm/providers/{provider_id}", response_model=LLMProviderResponse, tags=["admin-llm"])
def update_provider(
    provider_id: int,
    provider_data: LLMProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an LLM provider.
    Only ADMIN, SUPERADMIN or OWNER can execute.
    """
    membership = check_admin_permission(current_user, db)
    
    provider = db.query(LLMProvider).filter(
        LLMProvider.id == provider_id,
        LLMProvider.tenant_id == membership.tenant_id
    ).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    if provider_data.name is not None:
        provider.name = provider_data.name
    if provider_data.api_key is not None:
        provider.api_key_encrypted = encrypt_api_key(provider_data.api_key)
    if provider_data.api_base_url is not None:
        provider.api_base_url = provider_data.api_base_url
    if provider_data.is_active is not None:
        provider.is_active = provider_data.is_active
    
    db.commit()
    db.refresh(provider)
    
    return provider

@router.delete("/llm/providers/{provider_id}", tags=["admin-llm"])
def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an LLM provider.
    Only ADMIN, SUPERADMIN or OWNER can execute.
    """
    membership = check_admin_permission(current_user, db)
    
    provider = db.query(LLMProvider).filter(
        LLMProvider.id == provider_id,
        LLMProvider.tenant_id == membership.tenant_id
    ).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    db.delete(provider)
    db.commit()
    
    return {"message": "Provider deleted successfully"}

# ===== MODELS ENDPOINTS =====

@router.post("/llm/models", response_model=LLMModelResponse, tags=["admin-llm"])
def create_model(
    model_data: LLMModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new LLM model.
    Only ADMIN, SUPERADMIN or OWNER can execute.
    """
    membership = check_admin_permission(current_user, db)
    
    # Verify provider exists and belongs to the same tenant
    provider = db.query(LLMProvider).filter(
        LLMProvider.id == model_data.provider_id,
        LLMProvider.tenant_id == membership.tenant_id
    ).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    model = LLMModel(
        provider_id=model_data.provider_id,
        name=model_data.name,
        model_id=model_data.model_id,
        max_tokens=model_data.max_tokens,
        cost_per_1k_input_tokens=model_data.cost_per_1k_input_tokens,
        cost_per_1k_output_tokens=model_data.cost_per_1k_output_tokens,
        is_active=model_data.is_active
    )
    
    db.add(model)
    db.commit()
    db.refresh(model)
    
    return model

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
    
    query = db.query(LLMModel).join(LLMProvider).filter(
        LLMProvider.tenant_id == membership.tenant_id
    )
    
    if provider_id:
        query = query.filter(LLMModel.provider_id == provider_id)
    
    models = query.all()
    
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
    
    model = db.query(LLMModel).join(LLMProvider).filter(
        LLMModel.id == model_id,
        LLMProvider.tenant_id == membership.tenant_id
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return model

@router.patch("/llm/models/{model_id}", response_model=LLMModelResponse, tags=["admin-llm"])
def update_model(
    model_id: int,
    model_data: LLMModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an LLM model.
    Only ADMIN, SUPERADMIN or OWNER can execute.
    """
    membership = check_admin_permission(current_user, db)
    
    model = db.query(LLMModel).join(LLMProvider).filter(
        LLMModel.id == model_id,
        LLMProvider.tenant_id == membership.tenant_id
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    if model_data.name is not None:
        model.name = model_data.name
    if model_data.model_id is not None:
        model.model_id = model_data.model_id
    if model_data.max_tokens is not None:
        model.max_tokens = model_data.max_tokens
    if model_data.cost_per_1k_input_tokens is not None:
        model.cost_per_1k_input_tokens = model_data.cost_per_1k_input_tokens
    if model_data.cost_per_1k_output_tokens is not None:
        model.cost_per_1k_output_tokens = model_data.cost_per_1k_output_tokens
    if model_data.is_active is not None:
        model.is_active = model_data.is_active
    
    db.commit()
    db.refresh(model)
    
    return model

@router.delete("/llm/models/{model_id}", tags=["admin-llm"])
def delete_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an LLM model.
    Only ADMIN, SUPERADMIN or OWNER can execute.
    """
    membership = check_admin_permission(current_user, db)
    
    model = db.query(LLMModel).join(LLMProvider).filter(
        LLMModel.id == model_id,
        LLMProvider.tenant_id == membership.tenant_id
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    db.delete(model)
    db.commit()
    
    return {"message": "Model deleted successfully"}
