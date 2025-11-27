
"""
LLM Manager v4.5 - Multi-provider com registro de usage por tenant
"""
import os
import logging
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from app.models.models import Usage

logger = logging.getLogger(__name__)

# Modelos permitidos
OPENAI_MODELS = [m.strip() for m in os.getenv("OPENAI_ALLOWED_MODELS", "gpt-4o-mini,gpt-4.1,gpt-4.1-mini,gpt-4.1-nano,gpt-5").split(",") if m.strip()]
ANTHROPIC_MODELS = [m.strip() for m in os.getenv("ANTHROPIC_ALLOWED_MODELS", "claude-3.5-haiku,claude-3.5-sonnet").split(",") if m.strip()]
GOOGLE_MODELS = [m.strip() for m in os.getenv("GOOGLE_ALLOWED_MODELS", "gemini-1.5-pro,gemini-1.5-flash").split(",") if m.strip()]
DEFAULT_MODEL = os.getenv("OPENAI_MODEL_DEFAULT", "gpt-4o-mini")

def resolve_model(requested: Optional[str]) -> Tuple[str, str]:
    if not requested: return DEFAULT_MODEL, "openai"
    if requested in OPENAI_MODELS: return requested, "openai"
    if requested in ANTHROPIC_MODELS: return requested, "anthropic"
    if requested in GOOGLE_MODELS: return requested, "google"
    logger.warning(f"Modelo ‘{requested}’ não encontrado, usando default: {DEFAULT_MODEL}")
    return DEFAULT_MODEL, "openai"

def get_available_models() -> Dict[str, List[str]]:
    return {"openai": OPENAI_MODELS, "anthropic": ANTHROPIC_MODELS, "google": GOOGLE_MODELS}

def chat_completion(
    db: Session, tenant_id: int, user_id: int, messages: List[Dict[str, str]], 
    model: Optional[str] = None, temperature: float = 0.5, max_tokens: Optional[int] = None
) -> str:
    final_model, provider = resolve_model(model)
    logger.info(f"Chat completion: model={final_model}, provider={provider}, tenant={tenant_id}")

    if provider == "openai":
        response_text, usage_data = _chat_openai(messages, final_model, temperature, max_tokens)
    elif provider == "anthropic":
        response_text, usage_data = _chat_anthropic(messages, final_model, temperature, max_tokens)
    elif provider == "google":
        response_text, usage_data = _chat_google(messages, final_model, temperature, max_tokens)
    else:
        raise ValueError(f"Provedor desconhecido: {provider}")

    # Registrar usage
    if usage_data:
        _log_usage(db, tenant_id, user_id, final_model, usage_data)

    return response_text

def _chat_openai(messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: Optional[int]) -> Tuple[str, Dict]:
    import requests
    import time
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: raise ValueError("OPENAI_API_KEY não configurada")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": temperature}
    if max_tokens: payload["max_tokens"] = max_tokens

    response = requests.post(f"{os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')}/chat/completions", headers=headers, json=payload, timeout=60)
    response.raise_for_status() # Lança exceção para status >= 400
    
    result = response.json()
    usage = result.get("usage", {})
    return result["choices"][0]["message"]["content"], usage

def _chat_anthropic(messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: Optional[int]) -> Tuple[str, Dict]:
    # Implementação para Anthropic (Claude)
    return "Anthropic não implementado", {}

def _chat_google(messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: Optional[int]) -> Tuple[str, Dict]:
    # Implementação para Google (Gemini)
    return "Google não implementado", {}

def _log_usage(db: Session, tenant_id: int, user_id: int, model: str, usage_data: Dict):
    try:
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)

        if total_tokens > 0:
            usage_record = Usage(
                tenant_id=tenant_id,
                user_id=user_id,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                metric="tokens_used",
                amount=total_tokens
            )
            db.add(usage_record)
            db.commit()
    except Exception as e:
        logger.error(f"Falha ao registrar usage: {e}")
        db.rollback()
