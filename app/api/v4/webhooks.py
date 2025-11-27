"""
ORKIO v4.0 - Webhooks API for n8n Integration
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import hmac
import hashlib
from datetime import datetime

from app.core.database import get_db
from app.models.models import User, Tenant
from app.core.security import get_current_user_v4

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Webhook secret for HMAC validation (set in environment)
WEBHOOK_SECRET = "your_webhook_secret_here"  # TODO: Move to config


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify webhook signature using HMAC-SHA256
    """
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


@router.post("/n8n/document-processed")
async def webhook_document_processed(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Webhook para receber notificação de documento processado pelo n8n.
    
    **Payload esperado:**
    ```json
    {
        "document_id": 123,
        "status": "completed",
        "chunks_count": 42,
        "processing_time": 5.2,
        "metadata": {
            "filename": "document.pdf",
            "pages": 10
        }
    }
    ```
    
    **Headers:**
    - `X-Webhook-Signature`: HMAC-SHA256 signature of payload
    """
    # Verify signature
    body = await request.body()
    if x_webhook_signature:
        if not verify_webhook_signature(body, x_webhook_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Parse payload
    payload = await request.json()
    
    # TODO: Process webhook data
    # - Update document status
    # - Notify user
    # - Trigger next workflow step
    
    return {
        "status": "received",
        "timestamp": datetime.utcnow().isoformat(),
        "document_id": payload.get("document_id")
    }


@router.post("/n8n/rag-query")
async def webhook_rag_query(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Webhook para receber query RAG do n8n e retornar resultados.
    
    **Payload esperado:**
    ```json
    {
        "query": "O que é ORKIO?",
        "tenant_id": 1,
        "top_k": 3,
        "threshold": 0.6
    }
    ```
    
    **Response:**
    ```json
    {
        "results": [
            {
                "content": "...",
                "score": 0.85,
                "document_id": 123,
                "filename": "orkio_manual.pdf"
            }
        ],
        "total": 3
    }
    ```
    """
    # Verify signature
    body = await request.body()
    if x_webhook_signature:
        if not verify_webhook_signature(body, x_webhook_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Parse payload
    payload = await request.json()
    
    # TODO: Perform RAG search
    # - Use RAGService to search
    # - Return formatted results
    
    return {
        "results": [],
        "total": 0,
        "query": payload.get("query")
    }


@router.post("/n8n/chat-message")
async def webhook_chat_message(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Webhook para receber mensagem de chat do n8n e processar com agente.
    
    **Payload esperado:**
    ```json
    {
        "conversation_id": 456,
        "message": "Olá, como posso criar uma campanha?",
        "user_id": 1,
        "agent_id": 2
    }
    ```
    
    **Response:**
    ```json
    {
        "response": "Para criar uma campanha...",
        "message_id": 789,
        "timestamp": "2024-11-21T12:00:00Z"
    }
    ```
    """
    # Verify signature
    body = await request.body()
    if x_webhook_signature:
        if not verify_webhook_signature(body, x_webhook_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Parse payload
    payload = await request.json()
    
    # TODO: Process chat message
    # - Get conversation
    # - Get agent
    # - Generate response with LLM
    # - Save message
    # - Return response
    
    return {
        "response": "Webhook received, processing...",
        "message_id": None,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/n8n/health")
async def webhook_health():
    """
    Health check endpoint for n8n monitoring.
    """
    return {
        "status": "healthy",
        "service": "orkio-webhooks",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/n8n/trigger-workflow")
async def webhook_trigger_workflow(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Endpoint para ORKIO disparar workflows no n8n.
    
    **Payload esperado:**
    ```json
    {
        "workflow_name": "process_document",
        "data": {
            "document_id": 123,
            "tenant_id": 1
        }
    }
    ```
    
    **Response:**
    ```json
    {
        "status": "triggered",
        "workflow_id": "abc123",
        "execution_id": "xyz789"
    }
    ```
    """
    # Verify API key
    if not x_api_key or x_api_key != "your_n8n_api_key":  # TODO: Move to config
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Parse payload
    payload = await request.json()
    
    # TODO: Trigger n8n workflow via HTTP request
    # - Call n8n webhook URL
    # - Pass payload
    # - Return execution ID
    
    return {
        "status": "triggered",
        "workflow_name": payload.get("workflow_name"),
        "timestamp": datetime.utcnow().isoformat()
    }

