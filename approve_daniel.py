"""
Script para aprovar o usuário daniel@patroai.com diretamente no banco de dados
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL não encontrada no .env")
    exit(1)

print(f"Conectando ao banco de dados...")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Verificar se o usuário existe
    result = conn.execute(
        text("SELECT id, email, is_approved, status, role FROM users WHERE email = :email"),
        {"email": "daniel@patroai.com"}
    )
    user = result.fetchone()
    
    if user:
        print(f"\n✅ Usuário encontrado:")
        print(f"   ID: {user[0]}")
        print(f"   Email: {user[1]}")
        print(f"   Aprovado: {user[2]}")
        print(f"   Status: {user[3]}")
        print(f"   Role: {user[4]}")
        
        # Aprovar usuário
        conn.execute(
            text("""
                UPDATE users 
                SET is_approved = true, 
                    status = 'APPROVED', 
                    role = 'ADMIN'
                WHERE email = :email
            """),
            {"email": "daniel@patroai.com"}
        )
        conn.commit()
        
        print(f"\n✅ Usuário aprovado com sucesso!")
        print(f"\nCredenciais de acesso:")
        print(f"   Email: daniel@patroai.com")
        print(f"   Senha: Patro@2026")
        print(f"   Role: ADMIN")
    else:
        print("❌ Usuário não encontrado")
