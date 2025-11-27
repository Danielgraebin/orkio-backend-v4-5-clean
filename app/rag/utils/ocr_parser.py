"""
RAG OCR Parser - ORKIO v3.7.0
Parser para imagens com OCR (pytesseract)
"""

import logging
import os

logger = logging.getLogger(__name__)

ALLOW_OCR = os.getenv("ALLOW_OCR", "true").lower() == "true"


def parse_image_ocr(file_path: str) -> str:
    """Parse image com OCR (pytesseract)"""
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

