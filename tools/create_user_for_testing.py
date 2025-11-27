import os
import sys
import bcrypt
from sqlalchemy import create_engine, text

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/orkio"
engine = create_engine(DATABASE_URL)

# User data
email = "user@patro.ai"
password = "Patro@2025"
name = "Usuário Teste"

# Hash password
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

with engine.connect() as conn:
    # Check if user exists
    result = conn.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email})
    existing = result.fetchone()
    
    if existing:
        print(f"✅ Usuário {email} já existe (ID: {existing[0]})")
        user_id = existing[0]
    else:
        # Create user
        result = conn.execute(
            text("""
                INSERT INTO users (email, password_hash, name, role, is_approved, status, created_at)
                VALUES (:email, :password_hash, :name, 'USER', true, 'APPROVED', NOW())
                RETURNING id
            """),
            {"email": email, "password_hash": password_hash, "name": name}
        )
        user_id = result.fetchone()[0]
        conn.commit()
        print(f"✅ Usuário criado: {email} (ID: {user_id})")
    
    # Check if membership exists
    result = conn.execute(
        text("SELECT id FROM memberships WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    existing_membership = result.fetchone()
    
    if existing_membership:
        print(f"✅ Membership já existe (ID: {existing_membership[0]})")
    else:
        # Create membership for PATRO tenant (ID 1)
        result = conn.execute(
            text("""
                INSERT INTO memberships (user_id, tenant_id, role, created_at)
                VALUES (:user_id, 1, 'USER', NOW())
                RETURNING id
            """),
            {"user_id": user_id}
        )
        membership_id = result.fetchone()[0]
        conn.commit()
        print(f"✅ Membership criado para tenant PATRO (ID: {membership_id})")

print("\n🎉 Usuário USER criado com sucesso!")
print(f"\nCredenciais:")
print(f"  Email: {email}")
print(f"  Senha: {password}")
print(f"\nAcesso: /u/v4/chat")
