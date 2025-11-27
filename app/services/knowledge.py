# services/knowledge.py
# v3.9.0: Parse e vetorização conforme patch
from fastapi import UploadFile
from pydantic import BaseModel
from typing import List
import io, time

def _read_txt(raw: bytes) -> str:
    return raw.decode("utf-8", errors="ignore")

def _read_pdf(raw: bytes) -> str:
    # tenta pypdf, fallback pdfminer
    try:
        import pypdf
        pdf = pypdf.PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        from pdfminer.high_level import extract_text
        return extract_text(io.BytesIO(raw))

def _read_docx(raw: bytes) -> str:
    import docx
    bio = io.BytesIO(raw)
    doc = docx.Document(bio)
    return "\n".join(p.text for p in doc.paragraphs)

def extract_text(file: UploadFile, raw: bytes) -> str:
    """Extrai texto de TXT, PDF, DOCX"""
    name = file.filename.lower()
    if name.endswith(".txt") or name.endswith(".md"):
        return _read_txt(raw)
    if name.endswith(".pdf"):
        return _read_pdf(raw)
    if name.endswith(".docx"):
        return _read_docx(raw)
    # fallback binário – trata como txt
    return _read_txt(raw)

def chunk_text(text: str, max_tokens: int = 700) -> List[str]:
    """Split simples por tamanho de caractere ~2 tokens/char (aprox)"""
    sz = max_tokens * 2
    blocks = []
    i = 0
    while i < len(text):
        blocks.append(text[i:i+sz])
        i += sz
    return blocks

class VectorizeResult(BaseModel):
    chunks: int
    ms: int

def vectorize_document(session, tenant_id: int, document_id: str, text: str) -> VectorizeResult:
    """Vetoriza documento e salva chunks no banco"""
    from app.services.llm import embed_texts
    from app.models.models import KnowledgeItem, KnowledgeChunk
    
    start = time.time()
    chunks = chunk_text(text)
    embeddings = embed_texts(chunks)  # retorna list[list[float]]

    # Salvar chunks
    for idx, (content, emb) in enumerate(zip(chunks, embeddings)):
        session.add(KnowledgeChunk(
            item_id=document_id,
            idx=idx,
            text=content,
            embedding=emb
        ))
    
    # Atualizar status do documento
    session.query(KnowledgeItem).filter(KnowledgeItem.id==document_id).update({
        "status": "vectorized",
        "chunks_count": len(chunks)
    })
    session.commit()
    
    return VectorizeResult(chunks=len(chunks), ms=int((time.time()-start)*1000))

