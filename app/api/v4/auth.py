"""
ORKIO v4.0 - Rota de Autenticação
POST /api/v1/u/auth/login
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.models.models import User, Membership
from app.core.security import verify_password, get_password_hash
from app.core.auth_v4 import create_access_token
from app.models.models import Tenant
from datetime import datetime

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    tenant_id: int
    role: str
    email: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: int = 1


class RegisterResponse(BaseModel):
    id: int
    email: str
    role: str
    created_at: str


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Autentica usuário e retorna JWT com user_id, tenant_id e role
    """
    print(f"[DEBUG LOGIN] Email: {req.email}")
    print(f"[DEBUG LOGIN] Password length: {len(req.password)}")
    print(f"[DEBUG LOGIN] Password first 3 chars: {req.password[:3]}")
    
    # Buscar usuário por email
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos"
        )
    
    # Verificar senha
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos"
        )
    
    # Verificar status do usuário
    if user.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua conta está pendente de aprovação. Aguarde a aprovação de um administrador."
        )
    
    # Buscar membership (assumir primeiro tenant do usuário)
    membership = db.query(Membership).filter(
        Membership.user_id == user.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não possui tenant associado"
        )
    
    # Criar token JWT
    token_data = {
        "user_id": user.id,
        "tenant_id": membership.tenant_id,
        "role": membership.role,
        "email": user.email
    }
    access_token = create_access_token(data=token_data)
    
    return LoginResponse(
        access_token=access_token,
        user_id=user.id,
        tenant_id=membership.tenant_id,
        role=membership.role,
        email=user.email
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Registra novo usuário no sistema.
    Cria tenant pessoal e membership com role USER.
    """
    # Verificar se email já existe
    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já está em uso"
        )
    
    # Validar senha (mínimo 6 caracteres)
    if len(req.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha deve ter no mínimo 6 caracteres"
        )
    
    # Validar se o tenant_id existe
    tenant = db.query(Tenant).filter(Tenant.id == req.tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid tenant_id"
        )
    
    # Criar usuário com status PENDING (aguardando aprovação)
    hashed_password = get_password_hash(req.password)
    user = User(
        email=req.email,
        hashed_password=hashed_password,
        role="USER",
        is_approved=False,  # Aguardando aprovação do admin
        status="PENDING",   # Status pendente
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.flush()  # Obter user.id
    
    # Criar membership com tenant PATRO
    membership = Membership(
        user_id=user.id,
        tenant_id=tenant.id,  # Vinculado ao tenant PATRO
        role="USER"
    )
    db.add(membership)
    
    # Commit tudo
    db.commit()
    db.refresh(user)
    
    return RegisterResponse(
        id=user.id,
        email=user.email,
        role="USER",
        created_at=user.created_at.isoformat() if user.created_at else datetime.utcnow().isoformat()
    )



class LogoutResponse(BaseModel):
    success: bool
    message: str


@router.post("/logout", response_model=LogoutResponse)
def logout():
    """
    Logout do usuário
    
    No modelo JWT stateless, o logout é feito no client-side:
    - Frontend remove o token do localStorage/sessionStorage
    - Frontend limpa cookies
    - Frontend redireciona para /auth/login
    
    Para implementar blacklist de tokens, seria necessário:
    - Redis ou banco para armazenar tokens invalidados
    - Middleware para verificar blacklist em cada request
    
    Por enquanto, retornamos success=true para o frontend saber que pode limpar tudo.
    """
    return LogoutResponse(
        success=True,
        message="Logout realizado com sucesso. Token deve ser removido no client-side."
    )

