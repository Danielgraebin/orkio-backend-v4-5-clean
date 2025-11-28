"""
Importações de todos os modelos SQLAlchemy.
Este arquivo garante que todos os modelos sejam registrados em Base.metadata
quando o módulo app.models é importado.
"""

from .models import (
    Tenant,
    User,
    Membership,
    Agent,
    Document,
    KnowledgeChunk,
    Conversation,
    ConversationMessage,
    RAGEvent,
    AgentLink,
    MultiagentSession,
    MultiagentMessage,
    RoleEnum,
)

__all__ = [
    "Tenant",
    "User",
    "Membership",
    "Agent",
    "Document",
    "KnowledgeChunk",
    "Conversation",
    "ConversationMessage",
    "RAGEvent",
    "AgentLink",
    "MultiagentSession",
    "MultiagentMessage",
    "RoleEnum",
]
