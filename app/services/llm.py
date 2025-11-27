# backend/app/services/llm.py
"""
LLM Service - Unified interface for chat completions with RAG support
Uses llm_manager for multi-provider support
"""
import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Force load from .env file to override system environment
from dotenv import load_dotenv
load_dotenv(override=True)

from app.services.llm_manager import chat_completion as llm_chat, resolve_model

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

logger.info(f"LLM Service initialized")

if OPENAI_API_KEY is None:
    logger.warning("OPENAI_API_KEY not set — LLM will remain in STUB mode.")

def chat_completion(
    messages: List[Dict[str, Any]], 
    model: str = "gpt-4o-mini", 
    temperature: float = 0.4, 
    use_rag: bool = False, 
    tenant_id: Optional[int] = None, 
    agent_ids: Optional[List[int]] = None, 
    db = None
) -> Dict[str, Any]:
    """
    Chat completion with optional RAG support.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name (will be resolved via llm_manager)
        temperature: Temperature for generation
        use_rag: Whether to use RAG (knowledge base)
        tenant_id: Tenant ID for RAG filtering
        agent_ids: Agent IDs for RAG filtering
        db: Database session for RAG
    
    Returns:
        Dict with OpenAI-compatible response format
    """
    if OPENAI_API_KEY is None:
        raise RuntimeError("LLM integration not configured (OPENAI_API_KEY missing)")
    
    # RAG: Enrich context with knowledge base
    if use_rag and db and tenant_id:
        try:
            from app.services.vectorize import search_knowledge
            user_query = messages[-1]["content"] if messages else ""
            agent_id = agent_ids[0] if agent_ids else None
            
            logger.info(f"RAG search: query='{user_query[:50]}...', tenant={tenant_id}, agent={agent_id}")
            
            rag_results = search_knowledge(user_query, tenant_id, agent_id, db, top_k=3)
            
            if rag_results:
                context = "\n\n".join([
                    f"[Knowledge {i+1}]: {r['text'][:500]}" 
                    for i, r in enumerate(rag_results)
                ])
                
                # Insert context before last user message
                messages.insert(-1, {
                    "role": "system", 
                    "content": f"Context from knowledge base:\n{context}"
                })
                
                logger.info(f"RAG: Added {len(rag_results)} knowledge chunks to context")
            else:
                logger.info("RAG: No relevant knowledge found")
                
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            # Continue without RAG if it fails
    
    # Call LLM via manager
    try:
        final_model, provider = resolve_model(model)
        logger.info(f"Chat completion: model={final_model}, provider={provider}, temp={temperature}")
        
        response_text = llm_chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=1024
        )
        
        # Return OpenAI-compatible format
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "model": final_model,
            "usage": {
                "prompt_tokens": 0,  # Not tracked in this version
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        
    except Exception as e:
        logger.exception("LLM request failed: %s", e)
        raise



# v3.9.0: Embeddings conforme patch
def embed_texts(texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    """
    Gera embeddings para lista de textos usando OpenAI API.
    
    Args:
        texts: Lista de textos para embedar
        model: Modelo de embedding
    
    Returns:
        Lista de embeddings (list[list[float]])
    """
    import requests
    
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")
    
    url = f"{OPENAI_API_BASE}/embeddings"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.post(url, headers=headers, json={
            "model": model,
            "input": texts
        }, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return [d["embedding"] for d in data["data"]]
    except Exception as e:
        logger.error(f"Embedding API error: {e}")
        # Retorna embeddings vazios para não quebrar o fluxo
        return [[0.0] * 1536 for _ in texts]  # 1536 dims para text-embedding-3-small

