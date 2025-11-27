from fastapi import APIRouter
from . import auth_u, chat_u, conversations
# from . import apps_u, keys_u, usage_u, playground_u, billing_u, guardian_u, agents_u

users_router = APIRouter()

users_router.include_router(auth_u.router, prefix="/auth", tags=["u-auth"])
# users_router.include_router(apps_u.router, prefix="/apps", tags=["u-apps"])
# users_router.include_router(keys_u.router, prefix="/keys", tags=["u-keys"])
# users_router.include_router(usage_u.router, prefix="/usage", tags=["u-usage"])
# users_router.include_router(playground_u.router, prefix="/playground", tags=["u-playground"])
# users_router.include_router(billing_u.router, prefix="/billing", tags=["u-billing"])
# users_router.include_router(guardian_u.router, prefix="/guardian", tags=["u-guardian"])
# users_router.include_router(agents_u.router, tags=["u-agents"])
users_router.include_router(chat_u.router, tags=["u-chat"])
users_router.include_router(conversations.router, tags=["u-conversations"])
