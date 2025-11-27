from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import secrets
import hashlib

from app.core.database import get_db
from app.models.models import User

router = APIRouter(prefix="/password-reset", tags=["password-reset"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# In-memory token storage (for simplicity - in production use Redis or DB)
reset_tokens = {}


@router.post("/forgot")
async def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request password reset - generates a token and returns it
    (In production, this would send an email)
    """
    user = db.query(User).filter(User.email == req.email).first()
    
    if not user:
        # Don't reveal if email exists or not (security best practice)
        return {"message": "If the email exists, a reset link will be sent"}
    
    # Generate reset token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    # Store token (in production, save to DB with expiry)
    reset_tokens[token] = {
        "user_id": user.id,
        "email": user.email,
        "expires_at": expires_at
    }
    
    # In production, send email with reset link
    # For now, return token directly (for testing)
    return {
        "message": "If the email exists, a reset link will be sent",
        "token": token,  # Remove this in production!
        "reset_url": f"/auth/reset-password?token={token}"  # Remove this in production!
    }


@router.post("/reset")
async def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using token
    """
    # Validate token
    token_data = reset_tokens.get(req.token)
    
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    # Check expiry
    if datetime.utcnow() > token_data["expires_at"]:
        del reset_tokens[req.token]
        raise HTTPException(status_code=400, detail="Token expired")
    
    # Find user
    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hash new password
    from app.core.security import get_password_hash
    user.hashed_password = get_password_hash(req.new_password)
    
    db.commit()
    
    # Delete used token
    del reset_tokens[req.token]
    
    return {"message": "Password reset successfully"}


@router.get("/validate-token/{token}")
async def validate_token(token: str):
    """
    Validate if a reset token is valid and not expired
    """
    token_data = reset_tokens.get(token)
    
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid token")
    
    if datetime.utcnow() > token_data["expires_at"]:
        del reset_tokens[token]
        raise HTTPException(status_code=400, detail="Token expired")
    
    return {
        "valid": True,
        "email": token_data["email"]
    }

