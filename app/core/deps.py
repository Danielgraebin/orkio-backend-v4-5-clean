'''
Centralized dependencies for the ORKIO API.
'''
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.auth_v4 import get_current_user, get_current_user_tenant, CurrentUser

def get_db():
    """
    Dependency to get a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
