from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.models.models import Agent
from app.core.security import get_current_user_v4
from openai import OpenAI
import os

router = APIRouter()

class PlaygroundRequest(BaseModel):
    agent_id: int
    prompt: str

class PlaygroundResponse(BaseModel):
    response: str
    agent_name: str

@router.post("/run", response_model=PlaygroundResponse)
async def run_playground(
    request: PlaygroundRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_v4)
):
    """Executa um prompt no playground com um agente específico"""
    
    # Buscar agente
    agent = db.query(Agent).filter(
        Agent.id == request.agent_id,
        Agent.tenant_id == current_user["tenant_id"]
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Chamar OpenAI
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model=agent.model or "gpt-4.1-mini",
            messages=[
                {"role": "system", "content": agent.system_prompt or "Você é um assistente útil."},
                {"role": "user", "content": request.prompt}
            ],
            temperature=agent.temperature or 0.7
        )
        
        return PlaygroundResponse(
            response=response.choices[0].message.content,
            agent_name=agent.name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling LLM: {str(e)}")

