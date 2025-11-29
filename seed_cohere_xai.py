"""Script rápido para adicionar Cohere e xAI"""
import psycopg2
from datetime import datetime

DB_CONFIG = {
    "host": "aws-1-us-east-2.pooler.supabase.com",
    "port": 5432,
    "database": "postgres",
    "user": "postgres.tsnqnfakrxomistlqkfs",
    "password": "9J0D9cNKD79PbKhH",
    "sslmode": "require"
}

PROVIDERS = [
    {
        "name": "Cohere",
        "slug": "cohere",
        "models": [
            {"name": "Command R+", "model_id": "command-r-plus-08-2024", "temp": 0.7},
            {"name": "Command R", "model_id": "command-r-08-2024", "temp": 0.7},
            {"name": "Command", "model_id": "command", "temp": 0.7},
        ]
    },
    {
        "name": "xAI",
        "slug": "xai",
        "models": [
            {"name": "Grok 2", "model_id": "grok-2-latest", "temp": 0.7},
            {"name": "Grok 2 Mini", "model_id": "grok-2-mini-latest", "temp": 0.7},
        ]
    },
]

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

for p in PROVIDERS:
    cursor.execute("SELECT id FROM llm_providers WHERE slug = %s", (p["slug"],))
    result = cursor.fetchone()
    
    if result:
        provider_id = result[0]
        print(f"✅ {p['name']} já existe (ID: {provider_id})")
    else:
        cursor.execute(
            "INSERT INTO llm_providers (name, slug, enabled, created_at) VALUES (%s, %s, %s, %s) RETURNING id",
            (p["name"], p["slug"], True, datetime.utcnow())
        )
        provider_id = cursor.fetchone()[0]
        print(f"✅ {p['name']} criado (ID: {provider_id})")
    
    for m in p["models"]:
        cursor.execute(
            "SELECT id FROM llm_models WHERE provider_id = %s AND model_id = %s",
            (provider_id, m["model_id"])
        )
        if cursor.fetchone():
            print(f"  ⚠️  {m['name']} já existe")
        else:
            cursor.execute(
                "INSERT INTO llm_models (provider_id, name, model_id, enabled, default_temperature, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (provider_id, m["name"], m["model_id"], True, m["temp"], datetime.utcnow())
            )
            print(f"  ✅ {m['name']} adicionado")

conn.commit()
cursor.close()
conn.close()
print("\n🎉 Concluído!")
