"""
ORKIO v4 - Apps Router
Gerenciamento de aplicações/integrações
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_v4
from app.models.models import User

router = APIRouter()

@router.get("/apps")
async def list_apps(
    current_user: User = Depends(get_current_user_v4),
    db: Session = Depends(get_db)
):
    """
    Lista aplicações disponíveis para o usuário
    """
    # Por enquanto retorna lista vazia
    # TODO: Implementar sistema de apps
    return {
        "apps": [],
        "total": 0
    }

