"""
RAG Embeddings - ORKIO v3.7.0
Sistema de vetorização e chunking
"""

import logging
import os
from typing import List
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
)

EMBEDDING_MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-large")


def split_into_chunks(text: str, chunk_size: int = 1500, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks
    v3.7.0: Chunk size 1.5k tokens (~2k chars)
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        if chunk.strip():
            chunks.append(chunk.strip())
        
        start = end - overlap
    
    return chunks


def get_embedding(text: str) -> List[float]:
    """
    Get embedding vector from OpenAI
    v3.7.0: Using text-embedding-3-large (3072 dimensions)
    """
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    
    except Exception as e:
        logger.error(f"Embedding API error: {e}")
        # Return stub vector (3072 dimensions for text-embedding-3-large)
        return [0.0] * 3072


def vectorize_text(text: str) -> tuple[List[str], List[List[float]]]:
    """
    Vectorize text: chunk + embed
    Returns: (chunks, embeddings)
    """
    chunks = split_into_chunks(text)
    embeddings = []
    
    for chunk in chunks:
        embedding = get_embedding(chunk)
        embeddings.append(embedding)
    
    return chunks, embeddings

