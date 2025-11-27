"""
Serviço de Orquestração Multi-Agent v4.0
- Routing entre agents baseado em keywords
- Handoff automático ou manual
- Logging de sessões multi-agent
"""
import json
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.models import Agent, AgentLink, MultiagentSession, MultiagentMessage


class Orchestrator:
    """
    Gerencia routing e handoff entre agents.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_agent_links(self, from_agent_id: int) -> List[AgentLink]:
        """
        Busca links ativos de um agent.
        """
        links = self.db.query(AgentLink).filter(
            AgentLink.from_agent_id == from_agent_id,
            AgentLink.active == True
        ).order_by(AgentLink.priority.desc()).all()
        
        return links
    
    def should_handoff(
        self,
        message: str,
        from_agent_id: int
    ) -> Optional[Tuple[int, str]]:
        """
        Decide se deve fazer handoff para outro agent.
        
        Returns:
            (to_agent_id, reason) ou None
        """
        links = self.get_agent_links(from_agent_id)
        
        if not links:
            return None
        
        message_lower = message.lower()
        
        for link in links:
            # Parse trigger keywords (JSON array)
            if link.trigger_keywords:
                try:
                    keywords = json.loads(link.trigger_keywords)
                except:
                    keywords = []
                
                # Verificar se alguma keyword está na mensagem
                for keyword in keywords:
                    if keyword.lower() in message_lower:
                        return (
                            link.to_agent_id,
                            f"Keyword detectada: '{keyword}'"
                        )
        
        return None
    
    def create_multiagent_session(
        self,
        tenant_id: int,
        root_agent_id: int,
        topic: str
    ) -> MultiagentSession:
        """
        Cria nova sessão multi-agent.
        """
        session = MultiagentSession(
            tenant_id=tenant_id,
            root_agent_id=root_agent_id,
            topic=topic
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def log_multiagent_message(
        self,
        session_id: int,
        sender_agent_id: int,
        receiver_agent_id: int,
        content: str,
        model: str = "gpt-4.1-mini",
        latency_ms: int = 0
    ) -> MultiagentMessage:
        """
        Registra mensagem entre agents.
        """
        message = MultiagentMessage(
            session_id=session_id,
            sender_agent_id=sender_agent_id,
            receiver_agent_id=receiver_agent_id,
            content=content,
            model=model,
            latency_ms=latency_ms
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
    
    def get_agent_by_id(self, agent_id: int) -> Optional[Agent]:
        """
        Busca agent por ID.
        """
        return self.db.query(Agent).filter(Agent.id == agent_id).first()
    
    def execute_handoff(
        self,
        from_agent_id: int,
        to_agent_id: int,
        message: str,
        session_id: Optional[int] = None
    ) -> dict:
        """
        Executa handoff de um agent para outro.
        
        Returns:
            {
                "success": bool,
                "to_agent": Agent,
                "session_id": int,
                "message": str
            }
        """
        to_agent = self.get_agent_by_id(to_agent_id)
        
        if not to_agent:
            return {
                "success": False,
                "error": "Agent de destino não encontrado"
            }
        
        # Se não tem session_id, criar nova sessão
        if not session_id:
            from_agent = self.get_agent_by_id(from_agent_id)
            session = self.create_multiagent_session(
                tenant_id=to_agent.tenant_id,
                root_agent_id=from_agent_id,
                topic=message[:100]  # Primeiros 100 chars como tópico
            )
            session_id = session.id
        
        # Logar mensagem de handoff
        self.log_multiagent_message(
            session_id=session_id,
            sender_agent_id=from_agent_id,
            receiver_agent_id=to_agent_id,
            content=message
        )
        
        return {
            "success": True,
            "to_agent": to_agent,
            "session_id": session_id,
            "message": f"Handoff para {to_agent.name}"
        }

