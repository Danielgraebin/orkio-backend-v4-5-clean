
"""
Rotas User v4.5 - File Upload & Download com Multi-Tenant
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid

from app.core.deps import get_db, get_current_user, get_current_user_tenant
from app.models.models import Document, Conversation, User, ConversationMessage

router = APIRouter()

UPLOAD_DIR = "/home/ubuntu/orkio/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/files", response_model=dict, tags=["User Console - Files"])
async def upload_file(
    file: UploadFile = File(...),
    conversation_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant),
    db: Session = Depends(get_db)
):
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    contents = await file.read()
    file_size = len(contents)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"Arquivo muito grande. O máximo é 50MB.")

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    document = Document(
        tenant_id=tenant_id,
        filename=file.filename,
        storage_path=file_path,
        size_bytes=file_size,
        status="UPLOADED",
        user_id=current_user.id
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    if conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id, Conversation.tenant_id == tenant_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversa não encontrada.")
        
        # Adiciona uma mensagem ao chat informando sobre o upload
        message = ConversationMessage(
            conversation_id=conversation_id,
            role="system",
            content=f"Arquivo '{file.filename}' foi enviado com sucesso."
        )
        db.add(message)
        db.commit()

    return {
        "file_id": document.id,
        "filename": file.filename,
        "url": f"/v4/user/files/{document.id}",
        "status": "uploaded",
        "size_kb": round(file_size / 1024, 2),
        "created_at": document.created_at.isoformat()
    }

@router.get("/files/{file_id}", response_class=FileResponse, tags=["User Console - Files"])
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_user_tenant),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == file_id, Document.tenant_id == tenant_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado ou acesso negado.")

    if not os.path.exists(document.storage_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no disco.")

    return FileResponse(
        path=document.storage_path,
        filename=document.filename,
        media_type="application/octet-stream"
    )
