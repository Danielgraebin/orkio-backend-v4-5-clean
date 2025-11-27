"""
RAG Parsers - ORKIO v3.7.0
Parsers genéricos para extração de texto de documentos
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def parse_txt(file_path: str) -> str:
    """Parse TXT/Markdown com auto-detecção de encoding"""
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
    """Parse PDF com pypdf, fallback para pdfminer"""
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
    """Parse DOCX com python-docx"""
    from docx import Document
    
    doc = Document(file_path)
    paragraphs = [para.text for para in doc.paragraphs]
    text = "\n".join(paragraphs)
    
    logger.info(f"DOCX parsed: {len(text)} chars")
    return text


def parse_file(file_path: str, mime_type: str) -> str:
    """
    Parse file baseado no MIME type
    Returns extracted text content
    """
    if mime_type in ["text/plain", "text/markdown"]:
        return parse_txt(file_path)
    
    elif mime_type == "application/pdf":
        return parse_pdf(file_path)
    
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return parse_docx(file_path)
    
    else:
        raise ValueError(f"Unsupported MIME type: {mime_type}")

