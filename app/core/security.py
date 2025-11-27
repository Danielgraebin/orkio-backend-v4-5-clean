from datetime import datetime, timedelta, timezone
import jwt
import bcrypt
from app.core.config import settings

def get_password_hash(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against bcrypt or argon2 hash"""
    try:
        # Try bcrypt first
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        # Fallback to passlib for argon2 (old hashes)
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
            return pwd_context.verify(plain, hashed)
        except:
            return False

def create_access_token(data: dict | str = None, sub: str | int = None, tenant_id: int = None, role: str = None):
    """Aceita dict ou parâmetros individuais para compatibilidade"""
    if data and isinstance(data, str):
        payload = {"sub": data}
    elif data and isinstance(data, dict):
        payload = data.copy()
    else:
        payload = {}
        if sub:
            payload["sub"] = str(sub)
        if tenant_id:
            payload["tenant_id"] = int(tenant_id)
        if role:
            payload["role"] = role
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["exp"] = expire
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import User

security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def get_current_user_tenant(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Extrai tenant_id do JWT para Users Console"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No tenant_id in token")
        return tenant_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_tenant_id(user: User = Depends(get_current_user)) -> int:
    """Extrai tenant_id do user object (compatibilidade)"""
    tenant_id = getattr(user, "_tenant_id", None)
    if not tenant_id:
        # Fallback: tentar extrair do token diretamente
        return get_current_user_tenant()
    return tenant_id

def get_current_user_v4(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    """Get current user from v4 JWT token (uses user_id instead of sub)"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("user_id")  # v4 uses user_id
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    # Store tenant_id from token for easy access
    user._tenant_id = payload.get("tenant_id")
    return user

# Aliases para compatibilidade
hash_password = get_password_hash

