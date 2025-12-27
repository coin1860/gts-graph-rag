"""Temporary knowledge routes for chat sessions.

Endpoints:
- POST /api/chat/temp-upload - Upload file for session
- DELETE /api/chat/temp/{session_id} - Delete session temp data
"""

import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.auth.dependencies import get_current_active_user
from backend.config import settings
from backend.ingestion.temp_knowledge import (
    cleanup_session,
    has_temp_data,
    ingest_file_to_temp,
)
from backend.models.db_models import User

router = APIRouter(prefix="/api/chat", tags=["temp-knowledge"])

# Temp file storage directory
TEMP_UPLOAD_DIR = os.path.join(settings.chroma_persist_dir, "temp_uploads")


class TempUploadResponse(BaseModel):
    """Response for temp file upload."""

    success: bool
    file_id: str
    file_name: str
    chunks_created: int
    message: str


class TempStatusResponse(BaseModel):
    """Response for temp session status."""

    session_id: str
    has_data: bool


@router.post("/temp-upload", response_model=TempUploadResponse)
async def upload_temp_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    current_user: User = Depends(get_current_active_user),
):
    """Upload file for temporary session knowledge.

    Files are embedded to a session-specific ChromaDB collection
    and automatically cleaned up after 24 hours.

    Args:
        file: Uploaded file
        session_id: Frontend-generated UUID for session isolation
        current_user: Authenticated user

    Returns:
        Upload result with file_id and chunk count
    """
    # Validate session_id format
    try:
        uuid.UUID(session_id)
    except ValueError as err:
        raise HTTPException(
            status_code=400,
            detail="Invalid session_id format. Expected UUID.",
        ) from err

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Check file extension
    allowed_extensions = {".pdf", ".md", ".txt", ".docx", ".xlsx"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext} not supported. Allowed: {allowed_extensions}",
        )

    # Check file size (max 10MB for temp files)
    max_size = 10 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {max_size // 1024 // 1024}MB",
        )

    # Create temp upload directory for this session
    session_dir = os.path.join(TEMP_UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    # Generate unique file ID
    file_id = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = os.path.join(session_dir, file_id)

    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}",
        ) from e

    # Ingest to temp ChromaDB
    try:
        chunk_ids = await ingest_file_to_temp(
            session_id=session_id,
            file_path=file_path,
            file_name=file.filename,
        )
    except Exception as e:
        # Clean up file on error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process file: {str(e)}",
        ) from e

    return TempUploadResponse(
        success=True,
        file_id=file_id,
        file_name=file.filename,
        chunks_created=len(chunk_ids),
        message=f"File uploaded and processed: {len(chunk_ids)} chunks created",
    )


@router.get("/temp-status/{session_id}", response_model=TempStatusResponse)
async def get_temp_status(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Check if session has temp data."""
    return TempStatusResponse(
        session_id=session_id,
        has_data=has_temp_data(session_id),
    )


@router.delete("/temp/{session_id}")
async def delete_temp_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Delete temp data for a session.

    Called when chat session ends or user wants to clear temp data.
    """
    # Delete ChromaDB collection
    cleanup_session(session_id)

    # Delete temp files
    session_dir = os.path.join(TEMP_UPLOAD_DIR, session_id)
    if os.path.exists(session_dir):
        import shutil
        shutil.rmtree(session_dir)

    return {"success": True, "message": f"Temp data deleted for session {session_id}"}
