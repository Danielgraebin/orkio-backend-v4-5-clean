from fastapi import APIRouter
from app.api.v4 import llm_providers, auth, files
from app.api.v4.admin import agents, users_approval, users

admin_v4_router = APIRouter()

admin_v4_router.include_router(auth.router, prefix="/auth", tags=["admin-auth"])
admin_v4_router.include_router(agents.router, tags=["admin-agents"])
admin_v4_router.include_router(llm_providers.router, prefix="/llm", tags=["admin-llm"])
admin_v4_router.include_router(files.router, prefix="/files", tags=["files"])
admin_v4_router.include_router(users.router, tags=["admin-users"])
admin_v4_router.include_router(users_approval.router, tags=["admin-users"])

