from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import get_current_user_tenant

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("")
def get_billing_summary(db: Session = Depends(get_db), tenant_id: int = Depends(get_current_user_tenant)):
    """Retorna resumo de billing do tenant"""
    return {
        "tenant_id": tenant_id,
        "balance": 0,
        "usage_current_month": 0,
        "plan": "free"
    }

