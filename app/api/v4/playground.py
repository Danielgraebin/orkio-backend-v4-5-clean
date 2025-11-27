"""
ORKIO v4 - Playground Router
Endpoint para testar agentes com RAG
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user_v4
from app.models.models import User, Agent
from app.services.llm import chat_completion

router = APIRouter()

class PlaygroundRequest(BaseModel):
    agent_id: int
    message: str

@router.post("/run")
async def playground_run(
    payload: PlaygroundRequest,
    current_user: User = Depends(get_current_user_v4),
    db: Session = Depends(get_db)
):
    """
    Executa uma mensagem no playground com um agente específico
    """
    # Buscar agente
    agent = db.query(Agent).filter(
        Agent.id == payload.agent_id,
        Agent.tenant_id == current_user.tenant_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    try:
        # Obter resposta do LLM
        messages = [
            {"role": "system", "content": agent.system_prompt or "You are a helpful assistant."},
            {"role": "user", "content": payload.message}
        ]
        
        llm_response = chat_completion(
            messages=messages,
            model=agent.model or "gpt-4o-mini",
            temperature=agent.temperature or 0.7,
            use_rag=False,  # RAG desabilitado no playground por enquanto
            tenant_id=current_user.tenant_id,
            db=db
        )
        
        response = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "No response")
        
        return {
            "success": True,
            "response": response,
            "agent_name": agent.name
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running playground: {str(e)}"
        )

