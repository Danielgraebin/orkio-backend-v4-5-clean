"""
ORKIO v4.5 - File Upload
Endpoint para upload de arquivos em conversas
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth_v4 import get_current_user, CurrentUser
from app.models.models import Conversation
import os
import uuid
from datetime import datetime

router = APIRouter()

# Diretório de uploads
UPLOAD_DIR = "/home/ubuntu/orkio/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Tamanho máximo: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Extensões permitidas
ALLOWED_EXTENSIONS = {
    # Imagens
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    # Documentos
    ".pdf", ".doc", ".docx", ".txt", ".md",
    # Planilhas
    ".xls", ".xlsx", ".csv",
    # Outros
    ".json", ".xml", ".zip"
}


@router.post("/conversations/{conversation_id}/files")
async def upload_file(
    conversation_id: int,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload de arquivo para uma conversa.
    Retorna file_id para ser usado ao enviar mensagem.
    """
    # Verificar se conversa existe e pertence ao usuário
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.user_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Validar extensão
    filename = file.filename or "file"
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Ler conteúdo do arquivo
    content = await file.read()
    
    # Validar tamanho
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    # Gerar nome único
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    # Salvar arquivo
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Retornar informações do arquivo
    return {
        "file_id": file_id,
        "filename": filename,
        "size": len(content),
        "content_type": file.content_type,
        "path": file_path,
        "uploaded_at": datetime.utcnow().isoformat()
    }


@router.get("/files/{file_id}")
async def get_file(
    file_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna informações de um arquivo.
    (Em produção, verificar permissão de acesso)
    """
    # Procurar arquivo no diretório
    for filename in os.listdir(UPLOAD_DIR):
        if filename.startswith(file_id):
            file_path = os.path.join(UPLOAD_DIR, filename)
            stat = os.stat(file_path)
            
            return {
                "file_id": file_id,
                "filename": filename,
                "size": stat.st_size,
                "path": file_path,
                "exists": True
            }
    
    raise HTTPException(status_code=404, detail="File not found")


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deleta um arquivo.
    (Em produção, verificar permissão de acesso)
    """
    # Procurar e deletar arquivo
    for filename in os.listdir(UPLOAD_DIR):
        if filename.startswith(file_id):
            file_path = os.path.join(UPLOAD_DIR, filename)
            os.remove(file_path)
            return {"message": "File deleted successfully"}
    
    raise HTTPException(status_code=404, detail="File not found")

