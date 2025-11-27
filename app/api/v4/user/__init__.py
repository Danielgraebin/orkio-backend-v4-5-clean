"""
User Console v4 Router
Aggregates all user-facing endpoints
"""
from fastapi import APIRouter
from app.api.v4.user.agents import router as agents_router
from app.api.v4.user import files, document_processing, rag_search, playground, apps, usage
from app.api.v4 import conversations, chat, auth, password_reset

user_v4_router = APIRouter()

# Include sub-routers
user_v4_router.include_router(auth.router, prefix="/auth", tags=["user-auth"])
user_v4_router.include_router(agents_router, tags=["user-agents"])
user_v4_router.include_router(conversations.router, tags=["user-conversations"])
user_v4_router.include_router(chat.router, tags=["user-chat"])
user_v4_router.include_router(files.router, tags=["user-files"])
user_v4_router.include_router(document_processing.router, tags=["user-documents"])
user_v4_router.include_router(rag_search.router, tags=["user-rag"])
user_v4_router.include_router(password_reset.router, tags=["password-reset"])
