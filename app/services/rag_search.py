"""
RAG Search Service - Busca semântica em documentos
"""
from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.models import KnowledgeChunk, Document
from app.services.document_processor import DocumentProcessor


class RAGSearchService:
    """
    Serviço de busca semântica em documentos processados.
    """
    
    def __init__(self):
        self.processor = DocumentProcessor()
    
    def search(
        self,
        db: Session,
        query: str,
        tenant_id: int,
        top_k: int = 3
    ) -> List[dict]:
        """
        Busca chunks relevantes para a query usando similaridade de embeddings.
        
        Args:
            db: Sessão do banco
            query: Texto da busca
            tenant_id: ID do tenant (para filtrar documentos)
            top_k: Número de resultados a retornar
            
        Returns:
            Lista de dicts com chunks relevantes e metadados
        """
        # Gerar embedding da query
        query_embedding = self.processor.generate_embeddings_batch([query])[0]
        
        # Buscar chunks similares usando SQL direto (mais simples)
        # Usamos CAST para converter lista Python em vector
        sql = text("""
            SELECT 
                kc.id,
                kc.document_id,
                kc.content,
                kc.chunk_index,
                d.filename,
                d.tenant_id,
                (kc.embedding <=> CAST(:query_embedding AS vector)) AS distance
            FROM knowledge_chunks kc
            JOIN documents d ON kc.document_id = d.id
            WHERE d.tenant_id = :tenant_id
            ORDER BY distance
            LIMIT :top_k
        """)
        
        # Converter embedding para string no formato pgvector: [1.0,2.0,3.0]
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        results = db.execute(
            sql,
            {
                "query_embedding": embedding_str,
                "tenant_id": tenant_id,
                "top_k": top_k
            }
        ).fetchall()
        
        # Formatar resultados
        chunks = []
        for row in results:
            chunks.append({
                "chunk_id": row[0],
                "document_id": row[1],
                "content": row[2],
                "chunk_index": row[3],
                "filename": row[4],
                "distance": float(row[6]),
                "relevance_score": 1.0 - float(row[6])  # Converter distância em score
            })
        
        return chunks
    
    def search_by_conversation(
        self,
        db: Session,
        query: str,
        conversation_id: int,
        top_k: int = 3
    ) -> List[dict]:
        """
        Busca chunks relevantes filtrados por conversa.
        
        Nota: Por enquanto, busca em todos os documentos do tenant.
        TODO: Implementar vínculo documento-conversa.
        """
        # Buscar tenant_id da conversa
        from app.models.models import Conversation
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return []
        
        return self.search(db, query, conversation.tenant_id, top_k)

