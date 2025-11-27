# app/api/admin/agent_send.py
# v3.10.0: Mensagens entre agentes (Daniel → CFO)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.models import Agent, User
from app.core.security import get_current_user
from app.services.llm_manager import chat_completion as llm_chat
import logging
import time

logger = logging.getLogger(__name__)
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AgentSendRequest(BaseModel):
    from_agent_id: int
    to_agent_id: int
    message: str

@router.post("/agent-send")
def agent_send(
    payload: AgentSendRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user)
):
    """
    Envia mensagem de um agente para outro.
    v3.10.0: Cria agent_dialog e registra eventos
    """
    # Verificar se agentes existem
    from_agent = db.query(Agent).filter(Agent.id == payload.from_agent_id).first()
    to_agent = db.query(Agent).filter(Agent.id == payload.to_agent_id).first()
    
    if not from_agent or not to_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 1. Criar ou reutilizar agent_dialog
    try:
        # Buscar dialog existente entre esses agentes
        result = db.execute(text("""
            SELECT id FROM agent_dialogs 
            WHERE tenant_id = 1 
            ORDER BY created_at DESC 
            LIMIT 1
        """))
        row = result.fetchone()
        
        if row:
            dialog_id = row[0]
        else:
            # Criar novo dialog
            result = db.execute(text("""
                INSERT INTO agent_dialogs (tenant_id, root_trace_id, created_at)
                VALUES (1, :trace_id, NOW())
                RETURNING id
            """), {'trace_id': f'agent_send_{int(time.time())}'})
            dialog_id = result.scalar()
            db.commit()
    
    except Exception as e:
        logger.exception("Failed to create agent_dialog")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create dialog: {str(e)}")
    
    # 2. Registrar mensagem enviada
    try:
        db.execute(text("""
            INSERT INTO agent_dialog_events 
            (dialog_id, from_agent_id, to_agent_id, role, message, meta_json, created_at)
            VALUES (:dialog_id, :from_agent_id, :to_agent_id, 'agent', :message, :meta, NOW())
        """), {
            'dialog_id': dialog_id,
            'from_agent_id': payload.from_agent_id,
            'to_agent_id': payload.to_agent_id,
            'message': payload.message,
            'meta': '{"status":"sent"}'
        })
        db.commit()
    except Exception as e:
        logger.exception("Failed to log agent_dialog_event")
        db.rollback()
    
    # 3. Invocar agente "to_agent_id" (CFO) internamente
    try:
        messages = [
            {"role": "system", "content": to_agent.purpose or "You are a helpful assistant."},
            {"role": "user", "content": f"Mensagem de {from_agent.name}: {payload.message}"}
        ]
        
        response = llm_chat(
            messages=messages,
            model=to_agent.llm_model or "gpt-4.1-mini",
            temperature=to_agent.temperature or 0.7
        )
    
    except Exception as e:
        logger.exception("Failed to invoke agent")
        # Registrar erro
        try:
            db.execute(text("""
                INSERT INTO agent_dialog_events 
                (dialog_id, from_agent_id, to_agent_id, role, message, meta_json, created_at)
                VALUES (:dialog_id, :from_agent_id, :to_agent_id, 'system', :message, :meta, NOW())
            """), {
                'dialog_id': dialog_id,
                'from_agent_id': payload.to_agent_id,
                'to_agent_id': payload.from_agent_id,
                'message': f"Erro ao processar mensagem: {str(e)}",
                'meta': '{"status":"error"}'
            })
            db.commit()
        except:
            db.rollback()
        
        raise HTTPException(status_code=502, detail=f"Agent invocation failed: {str(e)}")
    
    # 4. Registrar resposta do agente
    try:
        db.execute(text("""
            INSERT INTO agent_dialog_events 
            (dialog_id, from_agent_id, to_agent_id, role, message, meta_json, created_at)
            VALUES (:dialog_id, :from_agent_id, :to_agent_id, 'agent', :message, :meta, NOW())
        """), {
            'dialog_id': dialog_id,
            'from_agent_id': payload.to_agent_id,
            'to_agent_id': payload.from_agent_id,
            'message': response,
            'meta': '{"status":"ok"}'
        })
        db.commit()
    except Exception as e:
        logger.exception("Failed to log response")
        db.rollback()
    
    # 5. Retornar resposta
    return {
        "ok": True,
        "dialog_id": dialog_id,
        "response": response
    }

