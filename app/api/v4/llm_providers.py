"""
LLM Providers and API Keys Management
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import SessionLocal
from app.core.auth_v4 import get_current_user
from app.core.encryption import encrypt_api_key, decrypt_api_key
from sqlalchemy import text

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Criptografia AES-256-GCM via app.core.encryption

class ProviderResponse(BaseModel):
    id: int
    name: str
    slug: str
    enabled: bool

class ModelResponse(BaseModel):
    id: int
    provider_id: int
    name: str
    model_id: str
    enabled: bool
    default_temperature: Optional[float]
    configured: bool  # Se tem API key configurada

class APIKeyRequest(BaseModel):
    provider_id: int
    model_id: Optional[int] = None
    api_key: str
    base_url: Optional[str] = None

class APIKeyStatusResponse(BaseModel):
    provider_id: int
    model_id: Optional[int]
    configured: bool
    base_url: Optional[str]

@router.get("/providers", response_model=List[ProviderResponse])
async def list_providers(
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lista todos os providers disponíveis"""
    result = db.execute(text("""
        SELECT id, name, slug, enabled
        FROM llm_providers
        ORDER BY id
    """))
    
    providers = []
    for row in result:
        providers.append({
            "id": row[0],
            "name": row[1],
            "slug": row[2],
            "enabled": row[3]
        })
    
    return providers

@router.get("/providers/{provider_id}/models", response_model=List[ModelResponse])
async def list_provider_models(
    provider_id: int,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lista modelos de um provider com status de configuração"""
    tenant_id = current_user.tenant_id
    
    result = db.execute(text("""
        SELECT 
            m.id, m.provider_id, m.name, m.model_id, m.enabled, m.default_temperature,
            CASE WHEN k.id IS NOT NULL THEN true ELSE false END as configured
        FROM llm_models m
        LEFT JOIN llm_api_keys k ON k.model_id = m.id AND k.tenant_id = :tenant_id
        WHERE m.provider_id = :provider_id
        ORDER BY m.id
    """), {"provider_id": provider_id, "tenant_id": tenant_id})
    
    models = []
    for row in result:
        models.append({
            "id": row[0],
            "provider_id": row[1],
            "name": row[2],
            "model_id": row[3],
            "enabled": row[4],
            "default_temperature": row[5],
            "configured": row[6]
        })
    
    return models

@router.post("/api-keys")
async def save_api_key(
    request: APIKeyRequest,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Salva ou atualiza chave API (criptografada)"""
    if current_user.role != "OWNER":
        raise HTTPException(status_code=403, detail="Only OWNER can configure API keys")
    
    tenant_id = current_user.tenant_id
    
    # Criptografar chave usando AES-256-GCM
    encrypted_key = encrypt_api_key(request.api_key)
    
    # Upsert
    db.execute(text("""
        INSERT INTO llm_api_keys (tenant_id, provider_id, model_id, encrypted_api_key, base_url, updated_at)
        VALUES (:tenant_id, :provider_id, :model_id, :encrypted_key, :base_url, NOW())
        ON CONFLICT (tenant_id, provider_id, model_id)
        DO UPDATE SET 
            encrypted_api_key = :encrypted_key,
            base_url = :base_url,
            updated_at = NOW()
    """), {
        "tenant_id": tenant_id,
        "provider_id": request.provider_id,
        "model_id": request.model_id,
        "encrypted_key": encrypted_key,
        "base_url": request.base_url
    })
    db.commit()
    
    return {"message": "API key saved successfully"}

@router.get("/api-keys/status/{provider_id}", response_model=APIKeyStatusResponse)
async def get_api_key_status(
    provider_id: int,
    model_id: Optional[int] = None,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Verifica se API key está configurada (não retorna o valor)"""
    tenant_id = current_user.tenant_id
    
    result = db.execute(text("""
        SELECT id, base_url
        FROM llm_api_keys
        WHERE tenant_id = :tenant_id 
          AND provider_id = :provider_id
          AND (model_id = :model_id OR (:model_id IS NULL AND model_id IS NULL))
    """), {
        "tenant_id": tenant_id,
        "provider_id": provider_id,
        "model_id": model_id
    })
    
    row = result.fetchone()
    
    return {
        "provider_id": provider_id,
        "model_id": model_id,
        "configured": row is not None,
        "base_url": row[1] if row else None
    }

@router.delete("/api-keys/{provider_id}")
async def delete_api_key(
    provider_id: int,
    model_id: Optional[int] = None,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Remove chave API"""
    if current_user.role != "OWNER":
        raise HTTPException(status_code=403, detail="Only OWNER can delete API keys")
    
    tenant_id = current_user.tenant_id
    
    db.execute(text("""
        DELETE FROM llm_api_keys
        WHERE tenant_id = :tenant_id 
          AND provider_id = :provider_id
          AND (model_id = :model_id OR (:model_id IS NULL AND model_id IS NULL))
    """), {
        "tenant_id": tenant_id,
        "provider_id": provider_id,
        "model_id": model_id
    })
    db.commit()
    
    return {"message": "API key deleted successfully"}

