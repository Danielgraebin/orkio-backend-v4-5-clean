"""
Script para popular o banco de dados com provedores e modelos LLM mais recentes.
Executar: python3 seed_llm_providers.py
"""

import asyncio
import sys
from pathlib import Path

# Adicionar o diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import LLMProvider, LLMModel
from app.core.config import get_settings
import os

settings = get_settings()

# Criar engine e session
# Converter asyncpg para psycopg2
database_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
engine = create_engine(database_url)
SessionLocal = sessionmaker(bind=engine)

# Dados dos provedores e modelos
PROVIDERS_DATA = [
    {
        "name": "OpenAI",
        "api_base_url": "https://api.openai.com/v1",
        "description": "OpenAI GPT models including GPT-4, GPT-4o, and o1 series",
        "models": [
            {"name": "GPT-4.1", "model_id": "gpt-4-turbo-2024-04-09", "context_window": 128000, "max_tokens": 4096},
            {"name": "GPT-4.1 Mini", "model_id": "gpt-4-turbo-preview", "context_window": 128000, "max_tokens": 4096},
            {"name": "GPT-4o", "model_id": "gpt-4o", "context_window": 128000, "max_tokens": 16384},
            {"name": "GPT-4o Mini", "model_id": "gpt-4o-mini", "context_window": 128000, "max_tokens": 16384},
            {"name": "GPT-3.5 Turbo", "model_id": "gpt-3.5-turbo", "context_window": 16385, "max_tokens": 4096},
            {"name": "o1 Preview", "model_id": "o1-preview", "context_window": 128000, "max_tokens": 32768},
            {"name": "o1 Mini", "model_id": "o1-mini", "context_window": 128000, "max_tokens": 65536},
        ]
    },
    {
        "name": "Anthropic",
        "api_base_url": "https://api.anthropic.com/v1",
        "description": "Anthropic Claude models with advanced reasoning capabilities",
        "models": [
            {"name": "Claude 3.5 Sonnet", "model_id": "claude-3-5-sonnet-20241022", "context_window": 200000, "max_tokens": 8192},
            {"name": "Claude 3.5 Haiku", "model_id": "claude-3-5-haiku-20241022", "context_window": 200000, "max_tokens": 8192},
            {"name": "Claude 3 Opus", "model_id": "claude-3-opus-20240229", "context_window": 200000, "max_tokens": 4096},
            {"name": "Claude 3 Sonnet", "model_id": "claude-3-sonnet-20240229", "context_window": 200000, "max_tokens": 4096},
            {"name": "Claude 3 Haiku", "model_id": "claude-3-haiku-20240307", "context_window": 200000, "max_tokens": 4096},
        ]
    },
    {
        "name": "Google",
        "api_base_url": "https://generativelanguage.googleapis.com/v1",
        "description": "Google Gemini models with multimodal capabilities",
        "models": [
            {"name": "Gemini 2.0 Flash", "model_id": "gemini-2.0-flash-exp", "context_window": 1000000, "max_tokens": 8192},
            {"name": "Gemini 1.5 Pro", "model_id": "gemini-1.5-pro-latest", "context_window": 2000000, "max_tokens": 8192},
            {"name": "Gemini 1.5 Flash", "model_id": "gemini-1.5-flash-latest", "context_window": 1000000, "max_tokens": 8192},
            {"name": "Gemini 1.0 Pro", "model_id": "gemini-1.0-pro-latest", "context_window": 32760, "max_tokens": 2048},
        ]
    },
    {
        "name": "Meta",
        "api_base_url": "https://api.together.xyz/v1",
        "description": "Meta Llama open-source models via Together AI",
        "models": [
            {"name": "Llama 3.3 70B", "model_id": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "context_window": 128000, "max_tokens": 4096},
            {"name": "Llama 3.2 90B Vision", "model_id": "meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo", "context_window": 128000, "max_tokens": 4096},
            {"name": "Llama 3.2 11B Vision", "model_id": "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo", "context_window": 128000, "max_tokens": 4096},
            {"name": "Llama 3.2 3B", "model_id": "meta-llama/Llama-3.2-3B-Instruct-Turbo", "context_window": 128000, "max_tokens": 4096},
            {"name": "Llama 3.2 1B", "model_id": "meta-llama/Llama-3.2-1B-Instruct-Turbo", "context_window": 128000, "max_tokens": 4096},
            {"name": "Llama 3.1 405B", "model_id": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "context_window": 130000, "max_tokens": 4096},
            {"name": "Llama 3.1 70B", "model_id": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "context_window": 130000, "max_tokens": 4096},
            {"name": "Llama 3.1 8B", "model_id": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo", "context_window": 130000, "max_tokens": 4096},
        ]
    },
    {
        "name": "Mistral",
        "api_base_url": "https://api.mistral.ai/v1",
        "description": "Mistral AI models optimized for performance and efficiency",
        "models": [
            {"name": "Mistral Large 2", "model_id": "mistral-large-2411", "context_window": 128000, "max_tokens": 4096},
            {"name": "Mistral Small", "model_id": "mistral-small-2409", "context_window": 32000, "max_tokens": 4096},
            {"name": "Codestral", "model_id": "codestral-2405", "context_window": 32000, "max_tokens": 4096},
            {"name": "Mixtral 8x7B", "model_id": "open-mixtral-8x7b", "context_window": 32000, "max_tokens": 4096},
            {"name": "Mixtral 8x22B", "model_id": "open-mixtral-8x22b", "context_window": 64000, "max_tokens": 4096},
        ]
    },
    {
        "name": "Cohere",
        "api_base_url": "https://api.cohere.ai/v1",
        "description": "Cohere Command models for enterprise applications",
        "models": [
            {"name": "Command R+", "model_id": "command-r-plus-08-2024", "context_window": 128000, "max_tokens": 4096},
            {"name": "Command R", "model_id": "command-r-08-2024", "context_window": 128000, "max_tokens": 4096},
            {"name": "Command", "model_id": "command", "context_window": 4096, "max_tokens": 4096},
        ]
    },
    {
        "name": "xAI",
        "api_base_url": "https://api.x.ai/v1",
        "description": "xAI Grok models with real-time information access",
        "models": [
            {"name": "Grok 2", "model_id": "grok-2-latest", "context_window": 128000, "max_tokens": 4096},
            {"name": "Grok 2 Mini", "model_id": "grok-2-mini-latest", "context_window": 128000, "max_tokens": 4096},
        ]
    },
]


def seed_llm_data():
    """Popula o banco com provedores e modelos LLM."""
    db = SessionLocal()
    
    try:
        print("🚀 Iniciando seed de provedores e modelos LLM...")
        
        for provider_data in PROVIDERS_DATA:
            # Verificar se provedor já existe
            existing_provider = db.query(LLMProvider).filter(
                LLMProvider.name == provider_data["name"]
            ).first()
            
            if existing_provider:
                print(f"⚠️  Provedor '{provider_data['name']}' já existe, pulando...")
                continue
            
            # Criar provedor
            provider = LLMProvider(
                name=provider_data["name"],
                api_base_url=provider_data["api_base_url"],
                description=provider_data["description"],
                is_active=True
            )
            db.add(provider)
            db.flush()  # Para obter o ID do provedor
            
            print(f"✅ Provedor '{provider_data['name']}' criado com sucesso!")
            
            # Criar modelos do provedor
            for model_data in provider_data["models"]:
                model = LLMModel(
                    provider_id=provider.id,
                    name=model_data["name"],
                    model_id=model_data["model_id"],
                    context_window=model_data["context_window"],
                    max_tokens=model_data["max_tokens"],
                    is_active=True
                )
                db.add(model)
                print(f"  ✅ Modelo '{model_data['name']}' ({model_data['model_id']}) adicionado")
        
        db.commit()
        print("\n🎉 Seed concluído com sucesso!")
        print(f"📊 Total de provedores: {len(PROVIDERS_DATA)}")
        total_models = sum(len(p["models"]) for p in PROVIDERS_DATA)
        print(f"📊 Total de modelos: {total_models}")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Erro ao executar seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_llm_data()
