from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_v4
from app.models.models import User

router = APIRouter()

@router.get("")
async def get_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v4)
):
    """Retorna estatísticas de uso (placeholder)"""
    return {
        "total_requests": 0,
        "total_tokens": 0,
        "cost": 0.0
    }

