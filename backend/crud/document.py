"""CRUD operations for Document entity."""


from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.models.db_models import Document, DocumentStatus, DocumentType


class DocumentCreate(BaseModel):
    """Schema for creating a document."""

    name: str
    doc_type: DocumentType
    org_id: int
    file_path: str | None = None
    source_url: str | None = None
    file_size: int | None = None


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    name: str | None = None
    status: DocumentStatus | None = None
    error_message: str | None = None
    chroma_ids: list[str] | None = None
    neo4j_node_ids: list[str] | None = None
    chunk_count: int | None = None


class DocumentResponse(BaseModel):
    """Response schema for document."""

    id: int
    name: str
    doc_type: DocumentType
    org_id: int
    file_path: str | None
    source_url: str | None
    status: DocumentStatus
    error_message: str | None
    file_size: int | None
    chunk_count: int | None

    class Config:
        from_attributes = True


def create_document(db: Session, doc_data: DocumentCreate) -> Document:
    """Create a new document record."""
    db_doc = Document(
        name=doc_data.name,
        doc_type=doc_data.doc_type,
        org_id=doc_data.org_id,
        file_path=doc_data.file_path,
        source_url=doc_data.source_url,
        file_size=doc_data.file_size,
        status=DocumentStatus.PENDING,
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc


def get_document(db: Session, doc_id: int) -> Document | None:
    """Get document by ID."""
    return db.query(Document).filter(Document.id == doc_id).first()


def get_documents(
    db: Session,
    org_id: int | None = None,
    org_ids: list[int] | None = None,
    status: DocumentStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Document]:
    """Get documents with optional filters.

    Args:
        org_id: Filter by single org ID
        org_ids: Filter by multiple org IDs
        status: Filter by document status
        skip: Pagination offset
        limit: Pagination limit

    """
    query = db.query(Document)

    if org_id is not None:
        query = query.filter(Document.org_id == org_id)
    elif org_ids is not None:
        query = query.filter(Document.org_id.in_(org_ids))

    if status is not None:
        query = query.filter(Document.status == status)

    return query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()


def get_documents_by_name(
    db: Session,
    name_query: str,
    org_ids: list[int] | None = None
) -> list[Document]:
    """Search documents by name."""
    query = db.query(Document).filter(Document.name.ilike(f"%{name_query}%"))

    if org_ids:
        query = query.filter(Document.org_id.in_(org_ids))

    return query.all()


def update_document(
    db: Session,
    doc_id: int,
    doc_data: DocumentUpdate
) -> Document | None:
    """Update a document."""
    db_doc = get_document(db, doc_id)
    if not db_doc:
        return None

    update_data = doc_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_doc, field, value)

    db.commit()
    db.refresh(db_doc)
    return db_doc


def update_document_status(
    db: Session,
    doc_id: int,
    status: DocumentStatus,
    error_message: str | None = None
) -> Document | None:
    """Update document status (convenience function)."""
    db_doc = get_document(db, doc_id)
    if not db_doc:
        return None

    db_doc.status = status
    if error_message:
        db_doc.error_message = error_message

    db.commit()
    db.refresh(db_doc)
    return db_doc


def set_document_ids(
    db: Session,
    doc_id: int,
    chroma_ids: list[str] = None,
    neo4j_node_ids: list[str] = None
) -> Document | None:
    """Set the chroma and neo4j IDs for deletion tracking."""
    db_doc = get_document(db, doc_id)
    if not db_doc:
        return None

    if chroma_ids is not None:
        db_doc.chroma_ids = chroma_ids
    if neo4j_node_ids is not None:
        db_doc.neo4j_node_ids = neo4j_node_ids

    db.commit()
    db.refresh(db_doc)
    return db_doc


def delete_document(db: Session, doc_id: int) -> Document | None:
    """Delete document record from database.
    Returns the document before deletion for cleanup purposes.
    """
    db_doc = get_document(db, doc_id)
    if not db_doc:
        return None

    # Return a copy of data needed for cleanup
    doc_copy = Document(
        id=db_doc.id,
        name=db_doc.name,
        file_path=db_doc.file_path,
        chroma_ids=db_doc.chroma_ids,
        neo4j_node_ids=db_doc.neo4j_node_ids,
        org_id=db_doc.org_id,
    )

    db.delete(db_doc)
    db.commit()

    return doc_copy
