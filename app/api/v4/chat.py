from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import AsyncGenerator
import json
import os
import asyncio
from app.core.database import get_db
from app.models.models import Conversation, ConversationMessage, Agent
from app.core.auth_v4 import get_current_user, CurrentUser
from app.services.rag_service import RAGService

router = APIRouter(prefix="/chat")


class ChatRequest(BaseModel):
    conversation_id: int
    message: str


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Endpoint de chat com pseudo-streaming SSE.
    Como a API OpenAI do Manus não suporta streaming real,
    fazemos a chamada sem streaming e simulamos chunks no backend.
    """
    
    # Validar conversa
    conversation = db.query(Conversation).filter(
        Conversation.id == request.conversation_id,
        Conversation.tenant_id == current_user.tenant_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Buscar agente
    agent = db.query(Agent).filter(Agent.id == conversation.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Extrair dados do agent ANTES do generator (para evitar detached instance)
    agent_system_prompt = agent.system_prompt or "Você é um assistente útil."
    agent_temperature = agent.temperature
    agent_model = agent.model or "gpt-4.1-mini"
    agent_id = agent.id
    
    # Salvar mensagem do usuário
    user_msg = ConversationMessage(
        conversation_id=request.conversation_id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    user_msg_id = user_msg.id
    
    # 🔥 RAG: Buscar contexto relevante e aumentar o system prompt
    rag_service = RAGService(db)
    rag_sources = []
    try:
        augmented_system_prompt, chunks_used, rag_sources = rag_service.retrieve_and_augment(
            query=request.message,
            agent_id=agent_id,
            conversation_id=request.conversation_id,
            message_id=user_msg_id,
            original_system_prompt=agent_system_prompt
        )
        print(f"[RAG] Chunks usados: {chunks_used}, Sources: {rag_sources}")
    except Exception as e:
        print(f"[RAG] Erro ao buscar contexto: {e}")
        augmented_system_prompt = agent_system_prompt
        chunks_used = 0
        rag_sources = []
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        """Gera stream SSE com pseudo-streaming"""
        try:
            # Buscar histórico de mensagens
            messages = db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == request.conversation_id
            ).order_by(ConversationMessage.created_at).all()
            
            # Preparar mensagens para OpenAI com RAG
            openai_messages = [
                {"role": "system", "content": augmented_system_prompt}
            ]
            
            for msg in messages:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Chamar OpenAI SEM streaming
            print(f"[DEBUG] Chamando OpenAI (NON-streaming) com {len(openai_messages)} mensagens")
            
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = client.chat.completions.create(
                model=agent_model,
                messages=openai_messages,
                temperature=agent_temperature,
                stream=False,  # ❌ Streaming não suportado no Manus
                timeout=30
            )
            
            # Validar resposta
            if not response.choices or not response.choices[0].message.content:
                print(f"[ERROR] OpenAI retornou resposta vazia: {response}")
                yield f"data: {json.dumps({'error': 'Resposta vazia da OpenAI'})}\\n\\n"
                return
            
            full_response = response.choices[0].message.content
            print(f"[DEBUG] Resposta recebida: {len(full_response)} chars")
            
            # Simular streaming dividindo em palavras
            words = full_response.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'delta': chunk})}\\n\\n"
                await asyncio.sleep(0.05)  # Delay para simular streaming
            
            # Salvar resposta completa no banco
            print(f"[DEBUG] Salvando resposta: {len(full_response)} chars")
            assistant_msg = ConversationMessage(
                conversation_id=request.conversation_id,
                role="assistant",
                content=full_response
            )
            db.add(assistant_msg)
            db.commit()
            print(f"[DEBUG] Resposta salva com ID {assistant_msg.id}")
            
            # Enviar evento de finalização com rag_sources
            yield f"data: {json.dumps({'delta': '', 'done': True, 'rag_sources': rag_sources})}\\n\\n"
            
        except Exception as e:
            print(f"[ERROR] Falha no chat: {e}")
            error_msg = f"Erro ao processar mensagem: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg})}\\n\\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Desabilitar buffering do nginx
        }
    )

