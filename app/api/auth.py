from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import User
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings

router = APIRouter(prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user with is_approved=False (pending approval)
    user = User(
        email=payload.email, 
        password_hash=get_password_hash(payload.password), 
        role="USER",
        is_approved=False
    )
    db.add(user)
    db.commit()
    return {"ok": True, "message": "Registration successful. Awaiting admin approval."}

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if user is approved
    if not user.is_approved:
        raise HTTPException(
            status_code=403, 
            detail={
                "error": "pending_approval",
                "message": "Acesso pendente de aprovação pelo administrador."
            }
        )
    
    token = create_access_token(str(user.id))
    return {"access_token": token, "token_type": "bearer", "role": user.role}

@router.post("/logout")
def logout():
    """Logout endpoint (client-side token removal)"""
    return {"status": "ok", "message": "Logged out successfully"}
