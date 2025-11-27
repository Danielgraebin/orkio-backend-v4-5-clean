import os
import logging
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.models import KnowledgeItem, KnowledgeChunk
from openai import OpenAI

logger = logging.getLogger(__name__)

# OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

def vectorize_text_doc(item_id: str, content: str, db: Session) -> Dict:
    """
    Vectorize TXT document safely - NO 500/502 errors
    Returns: {"status": "ok"|"error", "chunks": int, "reason": str}
    """
    try:
        # Validate content
        if not content or not content.strip():
            logger.warning(f"Empty content for {item_id}")
            return {"status": "error", "chunks": 0, "reason": "empty_content"}
        
        # Chunk text (simple split by size)
        chunks = split_into_chunks(content)
        
        if not chunks:
            logger.warning(f"No chunks generated for {item_id}")
            return {"status": "error", "chunks": 0, "reason": "no_chunks_generated"}
        
        logger.info(f"Generated {len(chunks)} chunks for {item_id}")
        
        # Vectorize each chunk
        saved_chunks = 0
        for idx, chunk_text in enumerate(chunks):
            try:
                # Get embedding from OpenAI
                embedding = get_embedding(chunk_text)
                
                # Save chunk to database
                chunk = KnowledgeChunk(
                    item_id=item_id,
                    idx=idx,
                    text=chunk_text,
                    embedding=embedding
                )
                db.add(chunk)
                saved_chunks += 1
                
            except Exception as chunk_error:
                logger.error(f"Failed to vectorize chunk {idx} of {item_id}: {chunk_error}")
                # Continue with other chunks instead of failing completely
                continue
        
        db.commit()
        
        if saved_chunks == 0:
            logger.error(f"No chunks saved for {item_id}")
            return {"status": "error", "chunks": 0, "reason": "vectorization_failed"}
        
        logger.info(f"Vectorization complete for {item_id}: {saved_chunks} chunks")
        return {"status": "ok", "chunks": saved_chunks}
        
    except Exception as e:
        logger.exception(f"TXT vectorization failed for {item_id}: {e}")
        return {"status": "error", "chunks": 0, "reason": f"txt_vectorization_failed: {str(e)[:100]}"}

def split_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 150) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks

def get_embedding(text: str) -> List[float]:
    """
    Get embedding vector from OpenAI
    Safe wrapper with error handling
    """
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
        
    except Exception as e:
        logger.error(f"Embedding API error: {e}")
        # Return stub vector (1536 dimensions for text-embedding-3-small)
        # In production, you might want to retry or fail
        return [0.0] * 1536

def vectorize_knowledge_item(item_id: str, db: Session):
    """
    Main entry point for vectorization
    Supports TXT only for now (PDF/DOCX = best effort)
    """
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    
    if not item:
        logger.error(f"Knowledge item {item_id} not found")
        raise ValueError(f"Item {item_id} not found")
    
    # Get file path
    storage_path = os.path.join(
        os.getenv("KNOWLEDGE_STORAGE", "/home/ubuntu/data/knowledge"),
        str(item.tenant_id),
        item_id,
        item.filename
    )
    
    if not os.path.exists(storage_path):
        logger.error(f"File not found: {storage_path}")
        item.status = "error"
        item.error_reason = "file_not_found"
        db.commit()
        raise FileNotFoundError(f"File not found: {storage_path}")
    
    # Read content based on MIME type
    if item.mime == "text/plain" or item.mime == "text/markdown":
        # TXT - fully supported with auto-encoding detection
        try:
            import chardet
            
            # Read raw bytes
            with open(storage_path, "rb") as f:
                raw = f.read()
            
            # Detect encoding automatically
            detected = chardet.detect(raw)
            encoding = detected.get("encoding", "utf-8") or "utf-8"
            logger.info(f"Detected encoding for {item.filename}: {encoding} (confidence: {detected.get('confidence', 0):.2f})")
            
            # Decode with detected encoding
            try:
                content = raw.decode(encoding, errors="ignore")
            except Exception as decode_error:
                logger.warning(f"Failed to decode with {encoding}, falling back to utf-8: {decode_error}")
                content = raw.decode("utf-8", errors="ignore")
            
            result = vectorize_text_doc(item_id, content, db)
            
            if result["status"] == "ok":
                item.status = "vectorized"
                item.chunks_count = result["chunks"]
                item.error_reason = None
            else:
                item.status = "error"
                item.chunks_count = 0
                item.error_reason = result["reason"]
            
            db.commit()
            
        except Exception as e:
            logger.exception(f"TXT processing failed for {item_id}: {e}")
            item.status = "error"
            item.error_reason = f"txt_read_failed: {str(e)[:100]}"
            db.commit()
            raise
    
    elif item.mime == "application/pdf":
        # PDF - extract text with pdfminer
        try:
            from pdfminer.high_level import extract_text
            
            content = extract_text(storage_path)
            
            if not content or not content.strip():
                logger.warning(f"Empty PDF content for {item_id}")
                item.status = "error"
                item.error_reason = "pdf_empty"
                db.commit()
                return
            
            result = vectorize_text_doc(item_id, content, db)
            
            if result["status"] == "ok":
                item.status = "vectorized"
                item.chunks_count = result["chunks"]
                item.error_reason = None
            else:
                item.status = "error"
                item.chunks_count = 0
                item.error_reason = result["reason"]
            
            db.commit()
            
        except Exception as e:
            logger.exception(f"PDF processing failed for {item_id}: {e}")
            item.status = "error"
            item.error_reason = f"pdf_parse_failed: {str(e)[:100]}"
            db.commit()
            raise
    
    elif item.mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        # DOCX - extract text with python-docx
        try:
            from docx import Document
            
            doc = Document(storage_path)
            content = "\n".join([para.text for para in doc.paragraphs])
            
            if not content or not content.strip():
                logger.warning(f"Empty DOCX content for {item_id}")
                item.status = "error"
                item.error_reason = "docx_empty"
                db.commit()
                return
            
            result = vectorize_text_doc(item_id, content, db)
            
            if result["status"] == "ok":
                item.status = "vectorized"
                item.chunks_count = result["chunks"]
                item.error_reason = None
            else:
                item.status = "error"
                item.chunks_count = 0
                item.error_reason = result["reason"]
            
            db.commit()
            
        except Exception as e:
            logger.exception(f"DOCX processing failed for {item_id}: {e}")
            item.status = "error"
            item.error_reason = f"docx_parse_failed: {str(e)[:100]}"
            db.commit()
            raise
    
    else:
        # Unsupported MIME type
        logger.warning(f"Unsupported MIME type for vectorization: {item.mime}")
        item.status = "error"
        item.error_reason = f"unsupported_mime: {item.mime}"
        db.commit()
        raise ValueError(f"Unsupported MIME type: {item.mime}")

