from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Pool ultra-conservador para Supabase free tier
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=1,  # Apenas 1 conexão permanente
    max_overflow=0,  # Sem conexões extras
    pool_pre_ping=True,  # Testa conexão antes de usar
    pool_recycle=300,  # Recicla conexões a cada 5min
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



