from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from hashlib import sha256
from typing import List
from app.core.database import SessionLocal
from app.models.models import Run, RunStatus, Agent, AgentLink
from app.core.config import settings
from app.services.llm import chat_completion
import uuid

router = APIRouter(prefix=f"{settings.API_V1_STR}/orchestrator", tags=["orchestrator"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RunCreate(BaseModel):
    root_agent_id: int
    depth: int = 0

def _chain_next_runs(db: Session, run: Run):
    """Encadear próximos runs baseado em links"""
    # Procura links para este agente raiz
    links = db.query(AgentLink).filter(
        AgentLink.source_agent_id == run.root_agent_id,
        AgentLink.trigger == "on_result",
        AgentLink.enabled == True
    ).all()
    
    for lk in links:
        if run.depth >= lk.max_depth:
            continue
        if lk.autonomy == "manual":
            continue
        
        next_status = RunStatus.waiting_approval.value if lk.autonomy == "assisted" else RunStatus.queued.value
        nxt = Run(
            trace_id=run.trace_id,
            root_agent_id=lk.target_agent_id,
            depth=run.depth + 1,
            status=next_status
        )
        db.add(nxt)
    db.commit()

@router.get("/runs")
def list_runs(db: Session = Depends(get_db)):
    return db.query(Run).order_by(Run.id.desc()).all()

@router.post("/runs")
async def create_run(payload: RunCreate, db: Session = Depends(get_db)):
    # Buscar agente raiz
    agent = db.query(Agent).filter(Agent.id == payload.root_agent_id).first()
    if not agent:
        raise HTTPException(404, "agent not found")
    
    # Criar run
    r = Run(
        trace_id=str(uuid.uuid4())[:12], 
        root_agent_id=payload.root_agent_id, 
        depth=payload.depth, 
        status=RunStatus.running.value
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    
    # Executar LLM
    try:
        prompt = f"Agente {agent.name}. Objetivo: {agent.purpose or 'Sem propósito definido.'}"
        messages = [{"role": "user", "content": prompt}]
        # Integrar RAG se habilitado no agente
        use_rag = getattr(agent, 'use_rag', False)
        tenant_id = 1  # Admin tenant stub
        llm_result = chat_completion(
            messages, 
            model="gpt-4o-mini", 
            temperature=agent.temperature or 0.4,
            use_rag=use_rag,
            tenant_id=tenant_id,
            agent_ids=[agent.id],
            db=db
        )
        result = llm_result["choices"][0]["message"]["content"]
        r.note = result[:500]  # Salvar resultado
        
        # Verificar links on_result
        links: List[AgentLink] = db.query(AgentLink).filter(
            AgentLink.source_agent_id == agent.id,
            AgentLink.trigger == "on_result",
            AgentLink.enabled == True
        ).all()
        
        # Determinar status final baseado em autonomia dos links
        if links:
            # Se todos os links são auto_safe, marca como done
            # Se algum é assisted, marca como waiting_approval
            has_assisted = any(l.autonomy == "assisted" for l in links)
            r.status = RunStatus.waiting_approval.value if has_assisted else RunStatus.done.value
        else:
            r.status = RunStatus.done.value
            
    except Exception as e:
        r.status = RunStatus.failed.value
        r.note = f"Error: {str(e)}"
    finally:
        db.commit()
        db.refresh(r)
    
    # Se status é done, encadear imediatamente
    if r.status == RunStatus.done.value:
        _chain_next_runs(db, r)
    
    return r

class ApproveBody(BaseModel):
    note: str | None = None

@router.post("/runs/{run_id}/approve")
def approve(run_id: int, body: ApproveBody, db: Session = Depends(get_db)):
    r = db.get(Run, run_id)
    if not r:
        raise HTTPException(status_code=404, detail="run_not_found")
    
    # Só permite aprovar quando aguardando aprovação
    if r.status != RunStatus.waiting_approval.value:
        raise HTTPException(
            status_code=409, 
            detail=f"invalid_status:{r.status}"
        )
    
    r.status = RunStatus.done.value
    decision_note = body.note or "approved"
    r.note = (r.note or "") + f"\n[Approved: {decision_note}]"
    
    db.commit()
    db.refresh(r)
    _chain_next_runs(db, r)
    return {"ok": True, "run_id": r.id, "status": r.status}

