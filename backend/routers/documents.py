"""Document admin routes - CRUD with file upload and ingestion."""

import os
import shutil
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.dependencies import AdminUser, get_current_active_user
from backend.config import settings
from backend.crud.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    create_document,
    delete_document,
    get_document,
    get_documents,
    set_document_ids,
    update_document,
    update_document_status,
)
from backend.crud.organization import get_organization
from backend.database import get_db
from backend.ingestion import delete_document_data, ingest_document
from backend.ingestion.temp_knowledge import load_urls_with_langchain
from backend.models.db_models import DocumentStatus, DocumentType, User

router = APIRouter(prefix="/api/admin/documents", tags=["admin-documents"])


class ConfluenceRequest(BaseModel):
    """Request for ingesting Confluence page."""

    url: str
    name: str
    org_id: int


async def run_ingestion(doc_id: int, db_url: str):
    """Background task to run document ingestion."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        doc = get_document(db, doc_id)
        if not doc:
            return

        org = get_organization(db, doc.org_id)
        if not org:
            update_document_status(db, doc_id, DocumentStatus.FAILED, "Organization not found")
            return

        # Update status to ingesting
        update_document_status(db, doc_id, DocumentStatus.INGESTING)

        # Run ingestion
        chroma_ids, neo4j_ids, chunk_count = await ingest_document(doc, org)

        # Update document with IDs
        set_document_ids(db, doc_id, chroma_ids, neo4j_ids)

        # Update to ingested
        update_document(db, doc_id, DocumentUpdate(
            status=DocumentStatus.INGESTED,
            chunk_count=chunk_count
        ))

    except Exception as e:
        update_document_status(db, doc_id, DocumentStatus.FAILED, str(e)[:500])
    finally:
        db.close()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    org_id: int = Form(...),
    background_tasks: BackgroundTasks = None,
    admin: AdminUser = None,
    db: Session = Depends(get_db)
):
    """Upload and ingest a document file (PDF, TXT, HTML)."""
    # Validate org exists
    org = get_organization(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Determine document type
    filename = file.filename or "document"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    type_map = {
        "pdf": DocumentType.PDF,
        "txt": DocumentType.TXT,
        "html": DocumentType.HTML,
        "htm": DocumentType.HTML,
        "docx": DocumentType.DOCX,
        "xlsx": DocumentType.XLSX,
    }

    doc_type = type_map.get(ext)
    if not doc_type:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    # Save file
    upload_dir = settings.upload_dir
    os.makedirs(upload_dir, exist_ok=True)

    file_id = str(uuid4())
    file_path = os.path.join(upload_dir, f"{file_id}.{ext}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(file_path)

    # Create document record
    doc = create_document(db, DocumentCreate(
        name=filename,
        doc_type=doc_type,
        org_id=org_id,
        file_path=file_path,
        file_size=file_size,
    ))

    # Start background ingestion
    if background_tasks:
        background_tasks.add_task(run_ingestion, doc.id, settings.database_url)

    return doc


@router.post("/confluence", response_model=DocumentResponse)
async def ingest_confluence(
    request: ConfluenceRequest,
    background_tasks: BackgroundTasks,
    admin: AdminUser,
    db: Session = Depends(get_db)
):
    """Ingest a Confluence page by URL."""
    # Validate org exists
    org = get_organization(db, request.org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Fetch content using shared logic
    pages = await load_urls_with_langchain([request.url])
    if not pages:
        raise HTTPException(status_code=400, detail="Could not fetch content from URL")

    content = pages[0]["content"]
    title = pages[0]["title"] or request.name

    # Save to file
    upload_dir = settings.upload_dir
    os.makedirs(upload_dir, exist_ok=True)
    file_id = str(uuid4())
    file_path = os.path.join(upload_dir, f"{file_id}.txt")
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"Title: {title}\nURL: {request.url}\n\n{content}")
    
    file_size = os.path.getsize(file_path)

    # Create document record
    doc = create_document(db, DocumentCreate(
        name=request.name or title,
        doc_type=DocumentType.CONFLUENCE,
        org_id=request.org_id,
        source_url=request.url,
        file_path=file_path,
        file_size=file_size,
    ))

    # Start background ingestion
    background_tasks.add_task(run_ingestion, doc.id, settings.database_url)

    return doc


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    org_id: int = None,
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    admin: AdminUser = None,
    db: Session = Depends(get_db)
):
    """List documents with optional filters."""
    status_enum = None
    if status:
        try:
            status_enum = DocumentStatus(status)
        except ValueError:
            pass

    docs = get_documents(
        db,
        org_id=org_id,
        status=status_enum,
        skip=skip,
        limit=limit
    )
    return docs


# Create a separate public router for non-admin document access
public_router = APIRouter(prefix="/api/documents", tags=["documents"])


@public_router.get("/search", response_model=list[DocumentResponse])
async def search_documents(
    org_ids: str = Query(..., description="Comma-separated org IDs"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Search documents by organization IDs.

    For regular users, only returns documents from their accessible organizations.
    """
    # Parse org_ids
    try:
        requested_org_ids = [int(x.strip()) for x in org_ids.split(",") if x.strip()]
    except ValueError as err:
        raise HTTPException(
            status_code=400, detail="Invalid org_ids format"
        ) from err

    # Filter to user's accessible orgs (admin can access all)
    from backend.models.db_models import UserRole
    if current_user.role != UserRole.ADMIN:
        user_org_ids = [org.id for org in current_user.organizations]
        requested_org_ids = [oid for oid in requested_org_ids if oid in user_org_ids]

    if not requested_org_ids:
        return []

    # Get ingested documents from allowed orgs
    all_docs = []
    for org_id in requested_org_ids:
        docs = get_documents(
            db,
            org_id=org_id,
            status=DocumentStatus.INGESTED,
            limit=100
        )
        all_docs.extend(docs)

    return all_docs


@router.get("/{doc_id}/view")
async def view_document(
    doc_id: int,
    admin: AdminUser,
    db: Session = Depends(get_db)
):
    """View/Download the original document."""
    doc = get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.doc_type == DocumentType.CONFLUENCE:
        if not doc.source_url:
            raise HTTPException(status_code=404, detail="Confluence URL not found")
        return RedirectResponse(url=doc.source_url)

    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Original file not found on disk")

    return FileResponse(
        path=doc.file_path,
        filename=doc.name,
        media_type="application/octet-stream"
    )


@router.delete("/{doc_id}")
async def delete_document_by_id(
    doc_id: int,
    admin: AdminUser,
    db: Session = Depends(get_db)
):
    """Delete document with cascade cleanup.
    Removes data from Neo4j and ChromaDB.
    """
    doc = get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Cleanup from Neo4j and ChromaDB
    cleanup_stats = await delete_document_data(doc, delete_file_on_disk=True)

    # Delete from database
    delete_document(db, doc_id)

    return {
        "message": "Document deleted successfully",
        "cleanup": cleanup_stats,
    }
