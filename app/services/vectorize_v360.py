"""
Vectorization Service v3.6.0 - ORKIO
Suporte completo: TXT, PDF, DOCX, Imagens (OCR), Áudio, Vídeo
"""

import os
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.models import KnowledgeItem, KnowledgeChunk
from app.services.rag_monitor import log_event
from openai import OpenAI
import mimetypes

logger = logging.getLogger(__name__)

# OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
)

EMBEDDING_MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-large")
FILE_MAX_MB = int(os.getenv("FILE_MAX_MB", 25))
ALLOW_OCR = os.getenv("ALLOW_OCR", "true").lower() == "true"
ALLOW_AUDIO = os.getenv("ALLOW_AUDIO", "true").lower() == "true"
ALLOW_VIDEO = os.getenv("ALLOW_VIDEO", "true").lower() == "true"

# Supported MIME types
SUPPORTED_TYPES = [
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]

if ALLOW_OCR:
    SUPPORTED_TYPES.extend(["image/jpeg", "image/png", "image/jpg"])

if ALLOW_AUDIO:
    SUPPORTED_TYPES.extend(["audio/mpeg", "audio/wav", "audio/mp3"])

if ALLOW_VIDEO:
    SUPPORTED_TYPES.extend(["video/mp4", "video/quicktime", "video/mov"])


def parse_txt(file_path: str) -> str:
    """Parse TXT/Markdown with auto-encoding detection"""
    import chardet
    
    with open(file_path, "rb") as f:
        raw = f.read()
    
    detected = chardet.detect(raw)
    encoding = detected.get("encoding", "utf-8") or "utf-8"
    logger.info(f"Detected encoding: {encoding} (confidence: {detected.get('confidence', 0):.2f})")
    
    try:
        content = raw.decode(encoding, errors="ignore")
    except Exception as e:
        logger.warning(f"Failed to decode with {encoding}, falling back to utf-8: {e}")
        content = raw.decode("utf-8", errors="ignore")
    
    return content


def parse_pdf(file_path: str) -> str:
    """Parse PDF with pypdf, fallback to pdfminer"""
    try:
        # Try pypdf first (faster)
        from pypdf import PdfReader
        
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        if text.strip():
            logger.info(f"PDF parsed with pypdf: {len(text)} chars")
            return text
    
    except Exception as e:
        logger.warning(f"pypdf failed, trying pdfminer: {e}")
    
    # Fallback to pdfminer
    try:
        from pdfminer.high_level import extract_text
        
        text = extract_text(file_path)
        logger.info(f"PDF parsed with pdfminer: {len(text)} chars")
        return text
    
    except Exception as e:
        logger.error(f"pdfminer also failed: {e}")
        raise ValueError(f"PDF parsing failed: {e}")


def parse_docx(file_path: str) -> str:
    """Parse DOCX with python-docx"""
    from docx import Document
    
    doc = Document(file_path)
    paragraphs = [para.text for para in doc.paragraphs]
    text = "\n".join(paragraphs)
    
    logger.info(f"DOCX parsed: {len(text)} chars")
    return text


def parse_image_ocr(file_path: str) -> str:
    """Parse image with OCR (pytesseract)"""
    if not ALLOW_OCR:
        raise ValueError("OCR not enabled")
    
    try:
        import pytesseract
        from PIL import Image
        
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        
        logger.info(f"Image OCR: {len(text)} chars")
        return text
    
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise ValueError(f"OCR failed: {e}")


def transcribe_audio(file_path: str) -> str:
    """Transcribe audio with OpenAI Whisper API"""
    if not ALLOW_AUDIO:
        raise ValueError("Audio transcription not enabled")
    
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        text = transcript.text
        logger.info(f"Audio transcribed: {len(text)} chars")
        return text
    
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        raise ValueError(f"Audio transcription failed: {e}")


def transcribe_video(file_path: str) -> str:
    """Transcribe video by extracting audio and transcribing"""
    if not ALLOW_VIDEO:
        raise ValueError("Video transcription not enabled")
    
    try:
        import subprocess
        import tempfile
        
        # Extract audio with ffmpeg
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
            audio_path = tmp_audio.name
        
        cmd = [
            "ffmpeg",
            "-i", file_path,
            "-vn",  # No video
            "-acodec", "libmp3lame",
            "-y",  # Overwrite
            audio_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Transcribe audio
        text = transcribe_audio(audio_path)
        
        # Cleanup
        os.remove(audio_path)
        
        logger.info(f"Video transcribed: {len(text)} chars")
        return text
    
    except Exception as e:
        logger.error(f"Video transcription failed: {e}")
        raise ValueError(f"Video transcription failed: {e}")


def parse_file(file_path: str, mime_type: str) -> str:
    """
    Parse file based on MIME type
    Returns extracted text content
    """
    if mime_type in ["text/plain", "text/markdown"]:
        return parse_txt(file_path)
    
    elif mime_type == "application/pdf":
        return parse_pdf(file_path)
    
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return parse_docx(file_path)
    
    elif mime_type in ["image/jpeg", "image/png", "image/jpg"]:
        return parse_image_ocr(file_path)
    
    elif mime_type in ["audio/mpeg", "audio/wav", "audio/mp3"]:
        return transcribe_audio(file_path)
    
    elif mime_type in ["video/mp4", "video/quicktime", "video/mov"]:
        return transcribe_video(file_path)
    
    else:
        raise ValueError(f"Unsupported MIME type: {mime_type}")


def split_into_chunks(text: str, chunk_size: int = 1500, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks
    v3.6.0: Increased chunk size to 1.5k tokens (~2k chars)
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
    v3.6.0: Using text-embedding-3-large (3072 dimensions)
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


def vectorize_text_doc(item_id: str, content: str, db: Session, tenant_id: int, trace_id: Optional[str] = None) -> Dict:
    """
    Vectorize text content
    Returns: {"status": "ok"|"error", "chunks": int, "reason": str}
    """
    try:
        # Validate content
        if not content or not content.strip():
            logger.warning(f"Empty content for {item_id}")
            
            if trace_id:
                log_event(db, tenant_id, "rag.embedding_failed", trace_id=trace_id, doc_id=item_id, status="failed", payload={"reason": "empty_content"})
            
            return {"status": "error", "chunks": 0, "reason": "empty_content"}
        
        # Log parsing success
        if trace_id:
            log_event(db, tenant_id, "rag.parsed", trace_id=trace_id, doc_id=item_id, status="success", payload={"content_length": len(content)})
        
        # Chunk text
        chunks = split_into_chunks(content)
        
        if not chunks:
            logger.warning(f"No chunks generated for {item_id}")
            return {"status": "error", "chunks": 0, "reason": "no_chunks_generated"}
        
        logger.info(f"Generated {len(chunks)} chunks for {item_id}")
        
        # Log chunking
        if trace_id:
            log_event(db, tenant_id, "rag.chunked", trace_id=trace_id, doc_id=item_id, status="success", payload={"chunks_count": len(chunks)})
        
        # Vectorize each chunk
        saved_chunks = 0
        for idx, chunk_text in enumerate(chunks):
            try:
                # Get embedding
                embedding = get_embedding(chunk_text)
                
                # Save chunk
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
                continue
        
        db.commit()
        
        if saved_chunks == 0:
            logger.error(f"No chunks saved for {item_id}")
            
            if trace_id:
                log_event(db, tenant_id, "rag.embedding_failed", trace_id=trace_id, doc_id=item_id, status="failed", payload={"reason": "no_chunks_saved"})
            
            return {"status": "error", "chunks": 0, "reason": "vectorization_failed"}
        
        # Log embedding success
        if trace_id:
            log_event(db, tenant_id, "rag.embedded", trace_id=trace_id, doc_id=item_id, status="success", payload={
                "chunks_count": saved_chunks,
                "embedding_model": EMBEDDING_MODEL,
                "embedding_dim": 3072
            })
        
        logger.info(f"Vectorization complete for {item_id}: {saved_chunks} chunks")
        return {"status": "ok", "chunks": saved_chunks}
    
    except Exception as e:
        logger.exception(f"Vectorization failed for {item_id}: {e}")
        
        if trace_id:
            log_event(db, tenant_id, "rag.embedding_failed", trace_id=trace_id, doc_id=item_id, status="failed", payload={"error": str(e)[:200]})
        
        return {"status": "error", "chunks": 0, "reason": f"vectorization_failed: {str(e)[:100]}"}


def vectorize_knowledge_item(item_id: str, db: Session, trace_id: Optional[str] = None):
    """
    Main entry point for vectorization v3.6.0
    Supports: TXT, PDF, DOCX, Images (OCR), Audio, Video
    """
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    
    if not item:
        logger.error(f"Knowledge item {item_id} not found")
        raise ValueError(f"Item {item_id} not found")
    
    tenant_id = item.tenant_id or 1
    
    # Get file path
    storage_path = os.path.join(
        os.getenv("KNOWLEDGE_STORAGE", "/home/ubuntu/data/knowledge"),
        str(tenant_id),
        item_id,
        item.filename
    )
    
    if not os.path.exists(storage_path):
        logger.error(f"File not found: {storage_path}")
        item.status = "error"
        item.error_reason = "file_not_found"
        db.commit()
        raise FileNotFoundError(f"File not found: {storage_path}")
    
    # Check file size
    file_size_mb = os.path.getsize(storage_path) / (1024 * 1024)
    if file_size_mb > FILE_MAX_MB:
        logger.error(f"File too large: {file_size_mb:.2f}MB > {FILE_MAX_MB}MB")
        item.status = "error"
        item.error_reason = f"file_too_large: {file_size_mb:.2f}MB"
        db.commit()
        raise ValueError(f"File too large: {file_size_mb:.2f}MB")
    
    # Check MIME type
    if item.mime not in SUPPORTED_TYPES:
        logger.error(f"Unsupported MIME type: {item.mime}")
        item.status = "error"
        item.error_reason = f"unsupported_mime: {item.mime}"
        db.commit()
        raise ValueError(f"Unsupported MIME type: {item.mime}")
    
    try:
        # Parse file
        logger.info(f"Parsing {item.mime} file: {item.filename}")
        content = parse_file(storage_path, item.mime)
        
        if not content or not content.strip():
            logger.warning(f"Empty content after parsing: {item_id}")
            item.status = "error"
            item.error_reason = "empty_content_after_parse"
            db.commit()
            return
        
        # Vectorize
        result = vectorize_text_doc(item_id, content, db, tenant_id, trace_id)
        
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
        logger.exception(f"Processing failed for {item_id}: {e}")
        item.status = "error"
        item.error_reason = f"processing_failed: {str(e)[:100]}"
        db.commit()
        
        if trace_id:
            log_event(db, tenant_id, "rag.embedding_failed", trace_id=trace_id, doc_id=item_id, status="failed", payload={"error": str(e)[:200]})
        
        raise


def is_mime_supported(mime_type: str) -> bool:
    """Check if MIME type is supported"""
    return mime_type in SUPPORTED_TYPES


def get_supported_extensions() -> List[str]:
    """Get list of supported file extensions"""
    extensions = [".txt", ".md", ".pdf", ".docx"]
    
    if ALLOW_OCR:
        extensions.extend([".jpg", ".jpeg", ".png"])
    
    if ALLOW_AUDIO:
        extensions.extend([".mp3", ".wav"])
    
    if ALLOW_VIDEO:
        extensions.extend([".mp4", ".mov"])
    
    return extensions

