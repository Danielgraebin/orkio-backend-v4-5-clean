"""
Script para popular o banco de dados com provedores e modelos LLM mais recentes.
Adaptado à estrutura real das tabelas no Supabase.
Executar: python3 seed_llm_final.py
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import re

# Credenciais do Supabase
DB_CONFIG = {
    "host": "aws-1-us-east-2.pooler.supabase.com",
    "port": 5432,
    "database": "postgres",
    "user": "postgres.tsnqnfakrxomistlqkfs",
    "password": "9J0D9cNKD79PbKhH",
    "sslmode": "require"
}


def create_slug(name):
    """Cria um slug a partir do nome."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug


# Dados dos provedores e modelos
PROVIDERS_DATA = [
    {
        "name": "OpenAI",
        "models": [
            {"name": "GPT-4.1", "model_id": "gpt-4-turbo-2024-04-09", "temperature": 0.7},
            {"name": "GPT-4.1 Mini", "model_id": "gpt-4-turbo-preview", "temperature": 0.7},
            {"name": "GPT-4o", "model_id": "gpt-4o", "temperature": 0.7},
            {"name": "GPT-4o Mini", "model_id": "gpt-4o-mini", "temperature": 0.7},
            {"name": "GPT-3.5 Turbo", "model_id": "gpt-3.5-turbo", "temperature": 0.7},
            {"name": "o1 Preview", "model_id": "o1-preview", "temperature": 1.0},
            {"name": "o1 Mini", "model_id": "o1-mini", "temperature": 1.0},
        ]
    },
    {
        "name": "Anthropic",
        "models": [
            {"name": "Claude 3.5 Sonnet", "model_id": "claude-3-5-sonnet-20241022", "temperature": 0.7},
            {"name": "Claude 3.5 Haiku", "model_id": "claude-3-5-haiku-20241022", "temperature": 0.7},
            {"name": "Claude 3 Opus", "model_id": "claude-3-opus-20240229", "temperature": 0.7},
            {"name": "Claude 3 Sonnet", "model_id": "claude-3-sonnet-20240229", "temperature": 0.7},
            {"name": "Claude 3 Haiku", "model_id": "claude-3-haiku-20240307", "temperature": 0.7},
        ]
    },
    {
        "name": "Google",
        "models": [
            {"name": "Gemini 2.0 Flash", "model_id": "gemini-2.0-flash-exp", "temperature": 0.7},
            {"name": "Gemini 1.5 Pro", "model_id": "gemini-1.5-pro-latest", "temperature": 0.7},
            {"name": "Gemini 1.5 Flash", "model_id": "gemini-1.5-flash-latest", "temperature": 0.7},
            {"name": "Gemini 1.0 Pro", "model_id": "gemini-1.0-pro-latest", "temperature": 0.7},
        ]
    },
    {
        "name": "Meta",
        "models": [
            {"name": "Llama 3.3 70B", "model_id": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "temperature": 0.7},
            {"name": "Llama 3.2 90B Vision", "model_id": "meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo", "temperature": 0.7},
            {"name": "Llama 3.2 11B Vision", "model_id": "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo", "temperature": 0.7},
            {"name": "Llama 3.2 3B", "model_id": "meta-llama/Llama-3.2-3B-Instruct-Turbo", "temperature": 0.7},
            {"name": "Llama 3.2 1B", "model_id": "meta-llama/Llama-3.2-1B-Instruct-Turbo", "temperature": 0.7},
            {"name": "Llama 3.1 405B", "model_id": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "temperature": 0.7},
            {"name": "Llama 3.1 70B", "model_id": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "temperature": 0.7},
            {"name": "Llama 3.1 8B", "model_id": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo", "temperature": 0.7},
        ]
    },
    {
        "name": "Mistral",
        "models": [
            {"name": "Mistral Large 2", "model_id": "mistral-large-2411", "temperature": 0.7},
            {"name": "Mistral Small", "model_id": "mistral-small-2409", "temperature": 0.7},
            {"name": "Codestral", "model_id": "codestral-2405", "temperature": 0.2},
            {"name": "Mixtral 8x7B", "model_id": "open-mixtral-8x7b", "temperature": 0.7},
            {"name": "Mixtral 8x22B", "model_id": "open-mixtral-8x22b", "temperature": 0.7},
        ]
    },
    {
        "name": "Cohere",
        "models": [
            {"name": "Command R+", "model_id": "command-r-plus-08-2024", "temperature": 0.7},
            {"name": "Command R", "model_id": "command-r-08-2024", "temperature": 0.7},
            {"name": "Command", "model_id": "command", "temperature": 0.7},
        ]
    },
    {
        "name": "xAI",
        "models": [
            {"name": "Grok 2", "model_id": "grok-2-latest", "temperature": 0.7},
            {"name": "Grok 2 Mini", "model_id": "grok-2-mini-latest", "temperature": 0.7},
        ]
    },
]


def seed_llm_data():
    """Popula o banco com provedores e modelos LLM."""
    conn = None
    cursor = None
    
    try:
        print("🚀 Conectando ao banco de dados...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🚀 Iniciando seed de provedores e modelos LLM...")
        
        for provider_data in PROVIDERS_DATA:
            slug = create_slug(provider_data["name"])
            
            # Verificar se provedor já existe
            cursor.execute(
                "SELECT id FROM llm_providers WHERE slug = %s",
                (slug,)
            )
            existing = cursor.fetchone()
            
            if existing:
                provider_id = existing["id"]
                print(f"⚠️  Provedor '{provider_data['name']}' já existe (ID: {provider_id})")
            else:
                # Criar provedor
                cursor.execute(
                    """
                    INSERT INTO llm_providers (name, slug, enabled, created_at)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        provider_data["name"],
                        slug,
                        True,
                        datetime.utcnow()
                    )
                )
                provider_id = cursor.fetchone()["id"]
                print(f"✅ Provedor '{provider_data['name']}' criado com sucesso! (ID: {provider_id})")
            
            # Criar modelos do provedor
            for model_data in provider_data["models"]:
                # Verificar se modelo já existe
                cursor.execute(
                    "SELECT id FROM llm_models WHERE provider_id = %s AND model_id = %s",
                    (provider_id, model_data["model_id"])
                )
                existing_model = cursor.fetchone()
                
                if existing_model:
                    print(f"  ⚠️  Modelo '{model_data['name']}' já existe")
                    continue
                
                cursor.execute(
                    """
                    INSERT INTO llm_models (
                        provider_id, name, model_id, enabled, default_temperature, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        provider_id,
                        model_data["name"],
                        model_data["model_id"],
                        True,
                        model_data["temperature"],
                        datetime.utcnow()
                    )
                )
                print(f"  ✅ Modelo '{model_data['name']}' ({model_data['model_id']}) adicionado")
        
        conn.commit()
        print("\n🎉 Seed concluído com sucesso!")
        print(f"📊 Total de provedores: {len(PROVIDERS_DATA)}")
        total_models = sum(len(p["models"]) for p in PROVIDERS_DATA)
        print(f"📊 Total de modelos: {total_models}")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n❌ Erro ao executar seed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    seed_llm_data()
