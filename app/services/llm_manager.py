
"""
LLM Manager v4.5 - Multi-provider com registro de usage por tenant
Suporta chaves de IA por tenant (Admin first) com fallback para env vars
"""
import os
import logging
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from app.models.models import Usage, LLMAPIKey, Tenant

logger = logging.getLogger(__name__)

# Modelos permitidos
OPENAI_MODELS = [m.strip() for m in os.getenv("ALLOWED_MODELS", "gpt-4.1-mini,gpt-4.1-nano,gemini-2.5-flash").split(",") if m.strip()]
ANTHROPIC_MODELS = [m.strip() for m in os.getenv("ANTHROPIC_ALLOWED_MODELS", "claude-3.5-haiku,claude-3.5-sonnet").split(",") if m.strip()]
GOOGLE_MODELS = [m.strip() for m in os.getenv("GOOGLE_ALLOWED_MODELS", "gemini-1.5-pro,gemini-1.5-flash").split(",") if m.strip()]
GROQ_MODELS = [m.strip() for m in os.getenv("GROQ_ALLOWED_MODELS", "mixtral-8x7b-32768").split(",") if m.strip()]
DEFAULT_MODEL = os.getenv("OPENAI_MODEL_DEFAULT", "gpt-4.1-mini")

def resolve_model(requested: Optional[str]) -> Tuple[str, str]:
    """Resolve o modelo e provider solicitado"""
    if not requested: 
        return DEFAULT_MODEL, "openai"
    if requested in OPENAI_MODELS: 
        return requested, "openai"
    if requested in ANTHROPIC_MODELS: 
        return requested, "anthropic"
    if requested in GOOGLE_MODELS: 
        return requested, "google"
    if requested in GROQ_MODELS:
        return requested, "groq"
    logger.warning(f"Modelo '{requested}' não encontrado, usando default: {DEFAULT_MODEL}")
    return DEFAULT_MODEL, "openai"

def get_available_models() -> Dict[str, List[str]]:
    """Retorna modelos disponíveis por provider"""
    return {
        "openai": OPENAI_MODELS, 
        "anthropic": ANTHROPIC_MODELS, 
        "google": GOOGLE_MODELS,
        "groq": GROQ_MODELS
    }

def get_api_key_for_tenant(db: Session, tenant_id: int, provider: str) -> Optional[str]:
    """
    Obtém a chave de API para um tenant específico
    Prioridade: 1) Chave do tenant no banco, 2) Variável de ambiente (fallback)
    """
    try:
        # Buscar chave do tenant no banco
        tenant_key = db.query(LLMAPIKey).filter(
            LLMAPIKey.tenant_id == tenant_id,
            LLMAPIKey.provider == provider,
            LLMAPIKey.is_active == True
        ).first()
        
        if tenant_key:
            logger.info(f"Usando chave de {provider} do tenant {tenant_id}")
            return tenant_key.api_key_encrypted  # Assumindo que está descriptografada no modelo
        
        # Fallback para variável de ambiente
        env_key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "groq": "GROQ_API_KEY"
        }
        
        env_key = env_key_map.get(provider)
        if env_key:
            fallback_key = os.getenv(env_key)
            if fallback_key:
                logger.info(f"Usando chave de {provider} do ambiente (fallback)")
                return fallback_key
        
        logger.warning(f"Nenhuma chave de {provider} encontrada para tenant {tenant_id}")
        return None
        
    except Exception as e:
        logger.error(f"Erro ao buscar chave de API para tenant {tenant_id}: {e}")
        # Fallback para env var em caso de erro
        env_key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "groq": "GROQ_API_KEY"
        }
        env_key = env_key_map.get(provider)
        return os.getenv(env_key) if env_key else None

def chat_completion(
    db: Session, tenant_id: int, user_id: int, messages: List[Dict[str, str]], 
    model: Optional[str] = None, temperature: float = 0.5, max_tokens: Optional[int] = None
) -> str:
    """
    Executa chat completion com modelo especificado
    Usa chaves de IA por tenant com fallback para env vars
    """
    final_model, provider = resolve_model(model)
    logger.info(f"Chat completion: model={final_model}, provider={provider}, tenant={tenant_id}, user={user_id}")

    # Obter chave de API para o tenant
    api_key = get_api_key_for_tenant(db, tenant_id, provider)
    if not api_key:
        raise ValueError(f"Nenhuma chave de API configurada para {provider} no tenant {tenant_id}")

    if provider == "openai":
        response_text, usage_data = _chat_openai(api_key, messages, final_model, temperature, max_tokens)
    elif provider == "anthropic":
        response_text, usage_data = _chat_anthropic(api_key, messages, final_model, temperature, max_tokens)
    elif provider == "google":
        response_text, usage_data = _chat_google(api_key, messages, final_model, temperature, max_tokens)
    elif provider == "groq":
        response_text, usage_data = _chat_groq(api_key, messages, final_model, temperature, max_tokens)
    else:
        raise ValueError(f"Provedor desconhecido: {provider}")

    # Registrar usage
    if usage_data:
        _log_usage(db, tenant_id, user_id, final_model, provider, usage_data)

    return response_text

def _chat_openai(api_key: str, messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: Optional[int]) -> Tuple[str, Dict]:
    """Chat completion via OpenAI API"""
    import requests
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": temperature}
    if max_tokens: 
        payload["max_tokens"] = max_tokens

    try:
        response = requests.post(
            f"{os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')}/chat/completions",
            headers=headers, 
            json=payload, 
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        usage = result.get("usage", {})
        return result["choices"][0]["message"]["content"], usage
    except Exception as e:
        logger.error(f"Erro ao chamar OpenAI: {e}")
        raise

def _chat_anthropic(api_key: str, messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: Optional[int]) -> Tuple[str, Dict]:
    """Chat completion via Anthropic API (Claude)"""
    try:
        from anthropic import Anthropic
        
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens or 1024,
            messages=messages,
            temperature=temperature
        )
        
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
        }
        return response.content[0].text, usage
    except Exception as e:
        logger.error(f"Erro ao chamar Anthropic: {e}")
        raise

def _chat_google(api_key: str, messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: Optional[int]) -> Tuple[str, Dict]:
    """Chat completion via Google Gemini API"""
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        client = genai.GenerativeModel(model)
        
        response = client.generate_content(
            messages,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens or 1024
            }
        )
        
        usage = {
            "prompt_tokens": 0,  # Google não expõe isso diretamente
            "completion_tokens": 0,
            "total_tokens": 0
        }
        return response.text, usage
    except Exception as e:
        logger.error(f"Erro ao chamar Google Gemini: {e}")
        raise

def _chat_groq(api_key: str, messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: Optional[int]) -> Tuple[str, Dict]:
    """Chat completion via Groq API"""
    try:
        from groq import Groq
        
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens or 1024
        )
        
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        return response.choices[0].message.content, usage
    except Exception as e:
        logger.error(f"Erro ao chamar Groq: {e}")
        raise

def _log_usage(db: Session, tenant_id: int, user_id: int, model: str, provider: str, usage_data: Dict):
    """Registra o consumo de tokens para o tenant"""
    try:
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)

        if total_tokens > 0:
            usage_record = Usage(
                tenant_id=tenant_id,
                user_id=user_id,
                model=model,
                provider=provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                metric="tokens_used",
                amount=total_tokens
            )
            db.add(usage_record)
            db.commit()
            logger.info(f"Usage registrado: tenant={tenant_id}, user={user_id}, tokens={total_tokens}")
    except Exception as e:
        logger.error(f"Falha ao registrar usage: {e}")
        db.rollback()
