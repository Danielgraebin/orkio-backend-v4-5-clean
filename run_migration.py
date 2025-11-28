#!/usr/bin/env python3
"""Script para executar migração da tabela tenants"""
import psycopg2
from urllib.parse import quote_plus

# Credenciais
password = quote_plus("Patro@2026")
DATABASE_URL = f"postgresql://postgres:{password}@db.tsnqnfakrxomistlqkfs.supabase.co:5432/postgres"

# Conectar ao banco
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

try:
    print("Iniciando migração da tabela tenants...")
    
    # Adicionar coluna slug
    print("1. Adicionando coluna 'slug'...")
    cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS slug VARCHAR(100)")
    
    # Adicionar coluna is_active
    print("2. Adicionando coluna 'is_active'...")
    cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL")
    
    # Adicionar coluna updated_at
    print("3. Adicionando coluna 'updated_at'...")
    cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    # Adicionar coluna default_provider
    print("4. Adicionando coluna 'default_provider'...")
    cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS default_provider VARCHAR(50)")
    
    # Adicionar coluna allowed_models
    print("5. Adicionando coluna 'allowed_models'...")
    cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS allowed_models JSONB")
    
    # Gerar slugs para tenants existentes
    print("6. Gerando slugs para tenants existentes...")
    cur.execute("""
        UPDATE tenants 
        SET slug = LOWER(REPLACE(name, ' ', '-'))
        WHERE slug IS NULL OR slug = ''
    """)
    
    # Tornar slug NOT NULL e UNIQUE
    print("7. Aplicando constraints em 'slug'...")
    cur.execute("ALTER TABLE tenants ALTER COLUMN slug SET NOT NULL")
    cur.execute("ALTER TABLE tenants ADD CONSTRAINT tenants_slug_unique UNIQUE (slug)")
    
    conn.commit()
    print("\n✅ Migração concluída com sucesso!")
    
    # Verificar resultado
    cur.execute("SELECT id, name, slug, is_active FROM tenants")
    tenants = cur.fetchall()
    print(f"\nTenants atualizados ({len(tenants)}):")
    for tenant in tenants:
        print(f"  - ID {tenant[0]}: {tenant[1]} (slug: {tenant[2]}, ativo: {tenant[3]})")
    
except psycopg2.errors.DuplicateColumn as e:
    print(f"⚠️  Coluna já existe: {e}")
    conn.rollback()
except Exception as e:
    print(f"❌ Erro na migração: {e}")
    conn.rollback()
    raise
finally:
    cur.close()
    conn.close()
