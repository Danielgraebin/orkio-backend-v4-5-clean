from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.config import settings

router = APIRouter(prefix=f"{settings.API_V1_STR}/usage", tags=["usage"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/summary")
def summary(period: str, db: Session = Depends(get_db)):
    # Stub para demo
    return {"period": period, "IA": 100, "DP": 50, "MCC": 1000}
