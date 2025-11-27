from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import User, Tenant, Membership
from app.core.security import hash_password, verify_password, create_access_token
from datetime import datetime

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str | None = None

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    # Verificar se email já existe
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="email_already_registered")
    
    # Criar tenant
    tenant = Tenant(name=payload.name or payload.email.split("@")[0])
    db.add(tenant)
    db.flush()
    
    # Criar usuário
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.user.value
    )
    db.add(user)
    db.flush()
    
    # Criar membership owner
    membership = Membership(
        user_id=user.id,
        tenant_id=tenant.id,
        role="owner"
    )
    db.add(membership)
    db.commit()
    db.refresh(user)
    db.refresh(tenant)
    
    # Gerar token com tenant_id e role
    token = create_access_token(
        sub=user.id,
        tenant_id=tenant.id,
        role="owner"
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "tenant_id": tenant.id,
        "role": "owner"
    }

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # Buscar usuário
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    
    # Buscar tenant via membership
    membership = db.query(Membership).filter(Membership.user_id == user.id).first()
    if not membership:
        raise HTTPException(status_code=400, detail="No workspace for user")
    
    # Gerar token com tenant_id e role
    token = create_access_token(
        sub=user.id,
        tenant_id=membership.tenant_id,
        role=membership.role
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "tenant_id": membership.tenant_id,
        "role": membership.role
    }

