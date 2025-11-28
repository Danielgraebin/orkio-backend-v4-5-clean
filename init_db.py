#!/usr/bin/env python
"""
Script para inicializar o banco de dados criando todas as tabelas.
Usa Base.metadata.create_all() para criar as tabelas definidas nos modelos SQLAlchemy.
"""

import os
import sys

# Configurar DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

print(f"📊 Using DATABASE_URL: {DATABASE_URL[:50]}...")

# Importar Base e engine
try:
    from app.core.database import Base, engine
    print("✅ Successfully imported Base and engine from app.core.database")
except ImportError as e:
    print(f"❌ ERROR: Failed to import Base and engine: {e}")
    sys.exit(1)

# Criar todas as tabelas
try:
    print("\n🔧 Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully!")
except Exception as e:
    print(f"❌ ERROR: Failed to create tables: {e}")
    sys.exit(1)

# Verificar se as tabelas foram criadas
try:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"\n📋 Tables in database ({len(tables)} total):")
    for table in sorted(tables):
        print(f"  ✅ {table}")
    
    if 'tenants' in tables:
        print("\n🎉 SUCCESS: tenants table exists!")
    else:
        print("\n⚠️  WARNING: tenants table NOT found")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ ERROR: Failed to verify tables: {e}")
    sys.exit(1)

print("\n✅ Database initialization completed successfully!")
