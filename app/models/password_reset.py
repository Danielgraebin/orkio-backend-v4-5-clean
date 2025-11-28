from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from datetime import datetime, timedelta
import secrets


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, server_default="false", nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    user = relationship("User")
    
    @staticmethod
    def generate_token():
        """Gera um token seguro de 32 caracteres"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def create_expiration(hours=24):
        """Cria data de expiração (padrão: 24 horas)"""
        return datetime.utcnow() + timedelta(hours=hours)
    
    def is_valid(self):
        """Verifica se o token ainda é válido"""
        return not self.used and datetime.utcnow() < self.expires_at
