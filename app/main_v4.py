"""
ORKIO v4.0 - Backend Oficial
Espinha dorsal limpa com rotas v4
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import Tenant, User, Membership, Agent
from app.core.security import get_password_hash

# Importar rotas v4
from app.api.v4 import auth, agents, conversations, chat, password_reset
from app.api.v4.admin import users as admin_users, agents as admin_agents, documents as admin_documents, agent_links as admin_agent_links, users_approval as admin_users_approval

app = FastAPI(
    title="ORKIO API v4.0",
    version="4.0.0",
    description="Multi-tenant AI Agent Platform"
)

# CORS
if settings.CORS_ORIGINS:
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
else:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas v4
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/u", tags=["auth"])
app.include_router(password_reset.router, prefix=f"{settings.API_V1_STR}/u", tags=["password-reset"])
app.include_router(agents.router, prefix=f"{settings.API_V1_STR}/u", tags=["agents"])
app.include_router(conversations.router, prefix=f"{settings.API_V1_STR}/u", tags=["conversations"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/u", tags=["chat"])
# User routers
from app.api.v4.user import playground, apps, usage
app.include_router(playground.router, prefix=f"{settings.API_V1_STR}/u/playground", tags=["playground"])
app.include_router(apps.router, prefix=f"{settings.API_V1_STR}/u/apps", tags=["apps"])
app.include_router(usage.router, prefix=f"{settings.API_V1_STR}/u/usage", tags=["usage"])

# Admin routes
app.include_router(admin_users.router, prefix=settings.API_V1_STR, tags=["admin-users"])
app.include_router(admin_users_approval.router, prefix=settings.API_V1_STR, tags=["admin-users-approval"])
app.include_router(admin_agents.router, prefix=settings.API_V1_STR, tags=["admin-agents"])
app.include_router(admin_documents.router, prefix=settings.API_V1_STR, tags=["admin-documents"])
app.include_router(admin_agent_links.router, prefix=settings.API_V1_STR, tags=["admin-agent-links"])


@app.get(f"{settings.API_V1_STR}/health")
def health():
    return {"status": "ok", "version": "4.0.0"}


def seed():
    """
    Seed inicial: cria tenant PATRO + usuário Daniel + agentes Daniel e CFO
    """
    db: Session = SessionLocal()
    try:
        # Criar tenant PATRO
        tenant = db.query(Tenant).filter(Tenant.name=="PATRO").first()
        if not tenant:
            tenant = Tenant(name="PATRO")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        
        # Criar usuário Daniel
        user = db.query(User).filter(User.email=="dangraebin@gmail.com").first()
        if not user:
            user = User(
                email="dangraebin@gmail.com",
                hashed_password=get_password_hash("Passw0rd!")
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Criar membership
        membership = db.query(Membership).filter(
            Membership.user_id==user.id,
            Membership.tenant_id==tenant.id
        ).first()
        if not membership:
            membership = Membership(
                user_id=user.id,
                tenant_id=tenant.id,
                role="OWNER"
            )
            db.add(membership)
            db.commit()
        
        # Criar agente Daniel
        daniel = db.query(Agent).filter(Agent.name=="Daniel", Agent.tenant_id==tenant.id).first()
        if not daniel:
            daniel = Agent(
                tenant_id=tenant.id,
                name="Daniel",
                system_prompt="Você é Daniel, CEO da PATRO. Responda de forma estratégica e direta.",
                temperature=0.7
            )
            db.add(daniel)
            db.commit()
        
        # Criar agente CFO
        cfo = db.query(Agent).filter(Agent.name=="CFO", Agent.tenant_id==tenant.id).first()
        if not cfo:
            cfo = Agent(
                tenant_id=tenant.id,
                name="CFO",
                system_prompt="Você é o CFO da PATRO. Analise questões financeiras com rigor e precisão.",
                temperature=0.5
            )
            db.add(cfo)
            db.commit()
            
        print("✅ Seed concluído: PATRO tenant + Daniel user + 2 agentes")
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    # Schema gerenciado via Alembic migrations
    seed()

