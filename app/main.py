from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.models.models import User
from app.core.security import get_password_hash
# from app.api import auth, agents, links, orchestrator, usage, guardian, knowledge
# from app.api.admin import agents_admin, users_admin, agent_dialogs, agent_send, rag_events
# from app.api.users import users_router
from app.api.admin_v4 import admin_v4_router
from app.api.v4.user import user_v4_router
from app.api.v4.webhooks import router as webhooks_router

app = FastAPI(title="ORKIO API", version="1.0.0")

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

# Routers Admin (comentados temporariamente para v4.0)
# app.include_router(auth.router)
# app.include_router(agents.router)
# app.include_router(links.router)
# app.include_router(orchestrator.router)
# app.include_router(usage.router)
# app.include_router(guardian.router)
# app.include_router(knowledge.router, prefix=f"{settings.API_V1_STR}/admin/knowledge", tags=["knowledge"])
# app.include_router(agents_admin.router)
# app.include_router(users_admin.router)
# app.include_router(agent_dialogs.router, prefix=f"{settings.API_V1_STR}/admin", tags=["agent-dialogs"])
# app.include_router(agent_send.router, prefix=f"{settings.API_V1_STR}/admin", tags=["agent-send"])
# app.include_router(rag_events.router, prefix=f"{settings.API_V1_STR}/admin", tags=["rag-events"])

# Users Console (temporariamente desabilitado para focar em v4)
# app.include_router(users_router, prefix=f"{settings.API_V1_STR}/u")

# Admin v4 Console
app.include_router(admin_v4_router, prefix=f"{settings.API_V1_STR}/admin")

# User v4 Console
app.include_router(user_v4_router, prefix=f"{settings.API_V1_STR}/u")

# Webhooks for n8n Integration
app.include_router(webhooks_router, prefix=f"{settings.API_V1_STR}")

@app.get(f"{settings.API_V1_STR}/health")
def health():
    return {"ok": True}

@app.get(f"{settings.API_V1_STR}/u/health", tags=["users"])
def users_health():
    return {"status": "ok", "scope": "users"}

def seed():
    from app.models.models import Tenant, User, Membership, Agent
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
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    # Schema gerenciado via Alembic migrations
    seed()
