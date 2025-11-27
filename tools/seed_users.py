#!/usr/bin/env python3.11
"""
Seed script para ORKIO v3.3 Users Console
Cria tenant, user owner, app e api_key idempotentemente
"""
import sys
import os
sys.path.append(os.getcwd())

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.models import Tenant, User, Membership, App, ApiKey
from app.core.security import hash_password
import secrets
import json

def generate_api_key():
    """Gera API key com prefixo ork_"""
    return f"ork_{secrets.token_urlsafe(16)}"

def seed():
    db: Session = SessionLocal()
    
    try:
        # 1. Tenant
        tenant = db.query(Tenant).filter(Tenant.name == "DemoCo").first()
        if not tenant:
            tenant = Tenant(name="DemoCo")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"✓ Tenant criado: {tenant.name} (id={tenant.id})")
        else:
            print(f"✓ Tenant já existe: {tenant.name} (id={tenant.id})")
        
        # 2. User owner
        user = db.query(User).filter(User.email == "owner@demo.co").first()
        if not user:
            user = User(
                email="owner@demo.co",
                password_hash=hash_password("Passw0rd!")
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✓ User criado: {user.email} (id={user.id})")
        else:
            print(f"✓ User já existe: {user.email} (id={user.id})")
        
        # 3. Membership
        memb = db.query(Membership).filter(
            Membership.user_id == user.id,
            Membership.tenant_id == tenant.id
        ).first()
        if not memb:
            memb = Membership(
                user_id=user.id,
                tenant_id=tenant.id,
                role="owner"
            )
            db.add(memb)
            db.commit()
            print(f"✓ Membership criado: user={user.id}, tenant={tenant.id}, role=owner")
        else:
            print(f"✓ Membership já existe: role={memb.role}")
        
        # 4. App
        app = db.query(App).filter(
            App.name == "Production",
            App.tenant_id == tenant.id
        ).first()
        if not app:
            app = App(
                name="Production",
                tenant_id=tenant.id
            )
            db.add(app)
            db.commit()
            db.refresh(app)
            print(f"✓ App criado: {app.name} (id={app.id})")
        else:
            print(f"✓ App já existe: {app.name} (id={app.id})")
        
        # 5. API Key
        existing_key = db.query(ApiKey).filter(ApiKey.app_id == app.id).first()
        if not existing_key:
            plaintext_key = generate_api_key()
            api_key = ApiKey(
                tenant_id=tenant.id,
                app_id=app.id,
                key_hash=hash_password(plaintext_key),  # hash para storage
                prefix=plaintext_key[:8]
            )
            db.add(api_key)
            db.commit()
            db.refresh(api_key)
            print(f"✓ API Key criado: {plaintext_key} (id={api_key.id})")
            
            # JSON final
            result = {
                "tenant": {"id": tenant.id, "name": tenant.name},
                "user": {"id": user.id, "email": user.email, "password": "Passw0rd!"},
                "app": {"id": app.id, "name": app.name},
                "api_key": {"plaintext": plaintext_key, "prefix": api_key.prefix}
            }
            print("\n" + "="*60)
            print("SEED COMPLETO:")
            print(json.dumps(result, indent=2))
            print("="*60)
        else:
            print(f"✓ API Key já existe (prefix={existing_key.prefix})")
            print("\n⚠️  API Key plaintext não pode ser recuperada (já foi gerada anteriormente)")
        
    except Exception as e:
        print(f"✗ Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()

