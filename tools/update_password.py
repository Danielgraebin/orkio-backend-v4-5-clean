import sys
sys.path.insert(0, '/home/ubuntu/orkio/backend')

import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql://orkio:orkio@localhost/orkio"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Update password
email = "dangraebin@gmail.com"
new_password = "Patro@2025"

# Hash password with bcrypt
hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

db = SessionLocal()
try:
    result = db.execute(
        text("UPDATE users SET hashed_password = :hash WHERE email = :email"),
        {"hash": hashed, "email": email}
    )
    db.commit()
    print(f"✅ Senha atualizada para {email}")
    print(f"Hash: {hashed[:50]}...")
except Exception as e:
    print(f"❌ Erro: {e}")
    db.rollback()
finally:
    db.close()

