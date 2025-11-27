
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user_tenant
from app.models.models import GuardianEvent
import io
import csv

router = APIRouter()

@router.get("/export", tags=["User Console - Guardian"])
def export_guardian_csv(db: Session = Depends(get_db), tenant_id: int = Depends(get_current_user_tenant)):
    """Exporta CSV de auditoria do tenant"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["id", "tenant_id", "user_id", "event_type", "details", "created_at"])
    
    events = db.query(GuardianEvent).filter(GuardianEvent.tenant_id == tenant_id).order_by(GuardianEvent.created_at.desc()).all()
    
    for event in events:
        writer.writerow([event.id, event.tenant_id, event.user_id, event.event_type, event.details, event.created_at.isoformat()])
    
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=guardian_tenant_{tenant_id}.csv"}
    )
