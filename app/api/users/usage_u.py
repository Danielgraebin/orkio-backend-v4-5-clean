
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.deps import get_db, get_current_user_tenant
from app.models.models import Usage
from datetime import datetime

router = APIRouter()

@router.get("", tags=["User Console - Usage"])
def get_usage(period: str | None = None, db: Session = Depends(get_db), tenant_id: int = Depends(get_current_user_tenant)):
    """
    Retorna agregado de uso por métrica (tokens_used, requests, etc.)
    period: YYYY-MM (opcional)
    """
    query = db.query(
        Usage.metric,
        func.sum(Usage.amount).label("total")
    ).filter(Usage.tenant_id == tenant_id)
    
    if period:
        try:
            year, month = map(int, period.split("-"))
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)
            
            query = query.filter(
                Usage.created_at >= start_date,
                Usage.created_at < end_date
            )
        except ValueError:
            # Ignora período inválido
            pass
    
    results = query.group_by(Usage.metric).all()
    
    # Retorna 0 para métricas não encontradas
    usage_map = {r.metric: r.total for r in results}
    metrics = ["tokens_used", "requests", "rag_searches"]
    
    return [
        {
            "metric": m,
            "total": usage_map.get(m, 0)
        }
        for m in metrics
    ]
