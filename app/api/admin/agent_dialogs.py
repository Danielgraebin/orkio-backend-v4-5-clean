# app/api/admin/agent_dialogs.py
# v3.9.0: Painel RG - Agent Dialog Monitor (CEO↔CFO, etc.)
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.models import User, Agent
from app.core.security import get_current_user
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ensure_admin(user: User):
    """Ensure user has admin privileges"""
    if user.role not in ("ADMIN", "OWNER"):
        raise HTTPException(status_code=403, detail="Admin access required")

# --- Models ---

class DialogSummary(BaseModel):
    id: int
    root_trace_id: str
    from_agent_id: int
    from_agent_name: str
    to_agent_id: int
    to_agent_name: str
    message_count: int
    status: str
    created_at: str

class DialogEvent(BaseModel):
    id: int
    from_agent_id: int
    from_agent_name: str
    to_agent_id: int
    to_agent_name: str
    role: str
    message: str
    meta_json: Optional[dict]
    created_at: str

class DialogDetail(BaseModel):
    id: int
    root_trace_id: str
    created_at: str
    events: List[DialogEvent]

# --- Endpoints ---

@router.get("/agent-dialogs")
def list_agent_dialogs(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    from_agent_id: Optional[int] = Query(None),
    to_agent_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar diálogos entre agentes (Painel RG).
    GET /admin/agent-dialogs?from_date=2025-11-01&to_date=2025-11-30&from_agent_id=6
    """
    ensure_admin(current_user)
    
    try:
        # Query base
        query = """
            SELECT 
                d.id,
                d.root_trace_id,
                d.created_at,
                e.from_agent_id,
                e.to_agent_id,
                COUNT(e.id) as message_count
            FROM agent_dialogs d
            LEFT JOIN agent_dialog_events e ON e.dialog_id = d.id
            WHERE 1=1
        """
        params = {}
        
        # Filtros
        if from_date:
            query += " AND d.created_at >= :from_date"
            params['from_date'] = from_date
        
        if to_date:
            query += " AND d.created_at <= :to_date"
            params['to_date'] = to_date
        
        if from_agent_id:
            query += " AND e.from_agent_id = :from_agent_id"
            params['from_agent_id'] = from_agent_id
        
        if to_agent_id:
            query += " AND e.to_agent_id = :to_agent_id"
            params['to_agent_id'] = to_agent_id
        
        query += """
            GROUP BY d.id, d.root_trace_id, d.created_at, e.from_agent_id, e.to_agent_id
            ORDER BY d.created_at DESC
            LIMIT 100
        """
        
        result = db.execute(text(query), params)
        
        dialogs = []
        for row in result:
            # Buscar nomes dos agentes
            from_agent = db.query(Agent).filter(Agent.id == row.from_agent_id).first()
            to_agent = db.query(Agent).filter(Agent.id == row.to_agent_id).first()
            
            dialogs.append({
                "id": row.id,
                "root_trace_id": row.root_trace_id,
                "from_agent_id": row.from_agent_id,
                "from_agent_name": from_agent.name if from_agent else "Unknown",
                "to_agent_id": row.to_agent_id,
                "to_agent_name": to_agent.name if to_agent else "Unknown",
                "message_count": row.message_count or 0,
                "status": "Concluído",  # TODO: calcular baseado em meta_json
                "created_at": row.created_at.isoformat() if row.created_at else None
            })
        
        return {"items": dialogs, "total": len(dialogs)}
        
    except Exception as e:
        logger.exception("List agent dialogs failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent-dialogs/{dialog_id}/events")
def get_dialog_events(
    dialog_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar eventos (timeline) de um diálogo específico.
    GET /admin/agent-dialogs/{dialog_id}/events
    """
    ensure_admin(current_user)
    
    try:
        # Verificar se diálogo existe
        dialog = db.execute(text("""
            SELECT id, root_trace_id, created_at
            FROM agent_dialogs
            WHERE id = :dialog_id
        """), {'dialog_id': dialog_id}).fetchone()
        
        if not dialog:
            raise HTTPException(status_code=404, detail="dialog_not_found")
        
        # Buscar eventos
        result = db.execute(text("""
            SELECT 
                id, 
                from_agent_id, 
                to_agent_id, 
                role, 
                message, 
                meta_json, 
                created_at
            FROM agent_dialog_events
            WHERE dialog_id = :dialog_id
            ORDER BY created_at ASC
        """), {'dialog_id': dialog_id})
        
        events = []
        for row in result:
            # Buscar nomes dos agentes
            from_agent = db.query(Agent).filter(Agent.id == row.from_agent_id).first()
            to_agent = db.query(Agent).filter(Agent.id == row.to_agent_id).first()
            
            events.append({
                "id": row.id,
                "from_agent_id": row.from_agent_id,
                "from_agent_name": from_agent.name if from_agent else "Unknown",
                "to_agent_id": row.to_agent_id,
                "to_agent_name": to_agent.name if to_agent else "Unknown",
                "role": row.role,
                "message": row.message,
                "meta_json": row.meta_json,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })
        
        return {
            "dialog": {
                "id": dialog.id,
                "root_trace_id": dialog.root_trace_id,
                "created_at": dialog.created_at.isoformat() if dialog.created_at else None
            },
            "events": events,
            "total": len(events)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Get dialog events failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent-dialogs/{dialog_id}/export")
def export_dialog_csv(
    dialog_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exportar eventos de um diálogo em formato CSV.
    GET /admin/agent-dialogs/{dialog_id}/export
    """
    ensure_admin(current_user)
    
    try:
        from fastapi.responses import StreamingResponse
        import io
        import csv
        
        # Buscar eventos
        result = db.execute(text("""
            SELECT 
                e.id,
                e.from_agent_id,
                e.to_agent_id,
                e.role,
                e.message,
                e.meta_json,
                e.created_at,
                a1.name as from_agent_name,
                a2.name as to_agent_name
            FROM agent_dialog_events e
            LEFT JOIN agents a1 ON a1.id = e.from_agent_id
            LEFT JOIN agents a2 ON a2.id = e.to_agent_id
            WHERE e.dialog_id = :dialog_id
            ORDER BY e.created_at ASC
        """), {'dialog_id': dialog_id})
        
        # Gerar CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'event_id', 'from_agent_id', 'from_agent_name', 
            'to_agent_id', 'to_agent_name', 'role', 'message', 
            'meta_json', 'created_at'
        ])
        
        for row in result:
            writer.writerow([
                row.id,
                row.from_agent_id,
                row.from_agent_name or 'Unknown',
                row.to_agent_id,
                row.to_agent_name or 'Unknown',
                row.role,
                row.message[:200] + '...' if len(row.message) > 200 else row.message,
                str(row.meta_json) if row.meta_json else '',
                row.created_at.isoformat() if row.created_at else ''
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=dialog_{dialog_id}_events.csv"}
        )
        
    except Exception as e:
        logger.exception("Export dialog CSV failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent-dialogs/overview")
def get_dialogs_overview(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Estatísticas agregadas de diálogos entre agentes.
    GET /admin/agent-dialogs/overview?from_date=2025-11-01&to_date=2025-11-30
    """
    ensure_admin(current_user)
    
    try:
        # Agentes mais acionados
        query = """
            SELECT 
                e.to_agent_id,
                a.name as agent_name,
                COUNT(DISTINCT e.dialog_id) as total_dialogs,
                AVG(CAST(e.meta_json->>'latency_ms' AS FLOAT)) as avg_latency_ms
            FROM agent_dialog_events e
            LEFT JOIN agents a ON a.id = e.to_agent_id
            LEFT JOIN agent_dialogs d ON d.id = e.dialog_id
            WHERE 1=1
        """
        params = {}
        
        if from_date:
            query += " AND d.created_at >= :from_date"
            params['from_date'] = from_date
        
        if to_date:
            query += " AND d.created_at <= :to_date"
            params['to_date'] = to_date
        
        query += """
            GROUP BY e.to_agent_id, a.name
            ORDER BY total_dialogs DESC
            LIMIT 10
        """
        
        result = db.execute(text(query), params)
        
        top_agents = []
        for row in result:
            top_agents.append({
                "agent_id": row.to_agent_id,
                "agent_name": row.agent_name or "Unknown",
                "total_dialogs": row.total_dialogs or 0,
                "avg_latency_ms": round(row.avg_latency_ms, 2) if row.avg_latency_ms else None
            })
        
        return {
            "top_agents": top_agents,
            "total_agents": len(top_agents)
        }
        
    except Exception as e:
        logger.exception("Get dialogs overview failed")
        raise HTTPException(status_code=500, detail=str(e))

