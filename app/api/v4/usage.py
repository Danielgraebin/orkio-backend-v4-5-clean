"""
ORKIO v4 - Usage Router
Estatísticas de uso da plataforma
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_v4
from app.models.models import User

router = APIRouter()

@router.get("/usage")
async def get_usage(
    current_user: User = Depends(get_current_user_v4),
    db: Session = Depends(get_db)
):
    """
    Retorna estatísticas de uso do usuário
    """
    # Por enquanto retorna dados vazios
    # TODO: Implementar tracking de uso
    return {
        "tokens_used": 0,
        "messages_count": 0,
        "agents_count": 0,
        "period": "current_month"
    }

