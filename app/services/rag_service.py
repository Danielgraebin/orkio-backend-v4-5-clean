
"""
Serviço RAG (Retrieval-Augmented Generation) v4.5
- Busca vetorial com pgvector e filtro por tenant
- Injeção de contexto no prompt
- Logging de eventos RAG com tenant_id
"""
import os
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.models import KnowledgeChunk, Document, RAGEvent
from openai import OpenAI

class RAGService:
    """
    Serviço para busca vetorial e recuperação de contexto com isolamento por tenant.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._client = None
        self.embedding_model = "text-embedding-3-small"
        self.top_k = 5
        self.similarity_threshold = 0.6
    
    @property
    def client(self):
        if self._client is None:
            self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._client
    
    def generate_query_embedding(self, query: str) -> List[float]:
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=query,
            encoding_format="float"
        )
        return response.data[0].embedding
    
    def search_similar_chunks(
        self,
        query_embedding: List[float],
        tenant_id: int,
        agent_id: int,
        top_k: Optional[int] = None
    ) -> List[Tuple[KnowledgeChunk, float]]:
        if top_k is None:
            top_k = self.top_k
        
        query = text("""
            SELECT 
                kc.id, kc.document_id, kc.content, kc.chunk_index, kc.embedding, kc.created_at,
                1 - (kc.embedding <=> :query_embedding::vector) as similarity
            FROM knowledge_chunks kc
            JOIN documents d ON kc.document_id = d.id
            WHERE d.tenant_id = :tenant_id AND d.agent_id = :agent_id
                AND d.status = 'READY' AND kc.embedding IS NOT NULL
            ORDER BY kc.embedding <=> :query_embedding::vector
            LIMIT :top_k
        """)
        
        result = self.db.execute(
            query,
            {
                "query_embedding": str(query_embedding), # Cast to string for psycopg3
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "top_k": top_k
            }
        )
        
        chunks_with_scores = []
        for row in result:
            chunk = KnowledgeChunk(
                id=row.id, document_id=row.document_id, content=row.content,
                chunk_index=row.chunk_index, embedding=row.embedding, created_at=row.created_at
            )
            similarity = float(row.similarity)
            
            if similarity >= self.similarity_threshold:
                chunks_with_scores.append((chunk, similarity))
        
        return chunks_with_scores
    
    def build_rag_context(self, chunks_with_scores: List[Tuple[KnowledgeChunk, float]]) -> str:
        if not chunks_with_scores:
            return ""
        
        context_parts = ["=== Base de Conhecimento Relevante ===\n"]
        MAX_CHUNK_LENGTH = 500
        
        for idx, (chunk, score) in enumerate(chunks_with_scores, 1):
            chunk_content = chunk.content[:MAX_CHUNK_LENGTH] + ("..." if len(chunk.content) > MAX_CHUNK_LENGTH else "")
            context_parts.append(f"[Fonte {idx} | Relevância: {score:.2f}]")
            context_parts.append(chunk_content)
            context_parts.append("")
        
        context_parts.append("=== Fim da Base de Conhecimento ===\n")
        return "\n".join(context_parts)
    
    def inject_context_into_system_prompt(self, original_system_prompt: str, rag_context: str) -> str:
        if not rag_context:
            return original_system_prompt
        
        return f"""{original_system_prompt}\n\n{rag_context}\n\nINSTRUÇÕES PARA USO DO CONTEXTO:\n1. Resuma e sintetize, não copie literalmente.\n2. Cite as fontes quando usar a informação.\n3. Se o contexto não for suficiente, informe que não encontrou a resposta na base de conhecimento."""

    def log_rag_event(self, tenant_id: int, conversation_id: int, message_id: int, query: str, chunks_retrieved: int, chunks_used: int):
        rag_event = RAGEvent(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            message_id=message_id,
            query=query,
            chunks_retrieved=chunks_retrieved,
            chunks_used=chunks_used
        )
        self.db.add(rag_event)
        self.db.commit()
    
    def retrieve_and_augment(
        self, query: str, tenant_id: int, agent_id: int, conversation_id: int, 
        message_id: int, original_system_prompt: str
    ) -> Tuple[str, int, List[dict]]:
        query_embedding = self.generate_query_embedding(query)
        chunks_with_scores = self.search_similar_chunks(query_embedding, tenant_id, agent_id)
        rag_context = self.build_rag_context(chunks_with_scores)
        augmented_prompt = self.inject_context_into_system_prompt(original_system_prompt, rag_context)
        
        rag_sources = []
        for chunk, score in chunks_with_scores:
            doc = self.db.query(Document).filter(Document.id == chunk.document_id).first()
            if doc:
                rag_sources.append({
                    "document_title": doc.filename,
                    "chunk_id": chunk.id,
                    "relevance": round(score, 2)
                })
        
        chunks_used = len(chunks_with_scores)
        self.log_rag_event(tenant_id, conversation_id, message_id, query, chunks_used, chunks_used)
        
        return augmented_prompt, chunks_used, rag_sources

# Helper function to be called from routes
def search(db: Session, tenant_id: int, agent_id: int, query: str) -> Tuple[List[str], int]:
    service = RAGService(db)
    query_embedding = service.generate_query_embedding(query)
    chunks_with_scores = service.search_similar_chunks(query_embedding, tenant_id, agent_id)
    
    context_blocks = [chunk.content for chunk, score in chunks_with_scores]
    return context_blocks, len(context_blocks)
