"""Database models for Organization, User, and Document entities."""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class UserRole(str, enum.Enum):
    """User roles for access control."""

    ADMIN = "admin"
    USER = "user"


class DocumentStatus(str, enum.Enum):
    """Document processing status."""

    PENDING = "pending"
    INGESTING = "ingesting"
    INGESTED = "ingested"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    """Supported document types."""

    PDF = "pdf"
    TXT = "txt"
    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"
    XLSX = "xlsx"
    CONFLUENCE = "confluence"


# Many-to-many relationship between users and organizations
user_organizations = Table(
    "user_organizations",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("organization_id", Integer, ForeignKey("organizations.id"), primary_key=True),
)


class Organization(Base):
    """Organization entity with optional GraphRAG configuration."""

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    graphrag_enabled = Column(Boolean, default=False)
    graph_schema = Column(JSON, nullable=True)  # {node_types, relationship_types, patterns}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = relationship("Document", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", secondary=user_organizations, back_populates="organizations")

    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name}, graphrag={self.graphrag_enabled})>"


class User(Base):
    """User entity with role-based access control."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organizations = relationship("Organization", secondary=user_organizations, back_populates="users")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class Document(Base):
    """Document entity with ingestion tracking."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    doc_type = Column(Enum(DocumentType), nullable=False)
    file_path = Column(String(500), nullable=True)  # Null for confluence links
    source_url = Column(String(1000), nullable=True)  # For confluence links
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING)
    error_message = Column(String(1000), nullable=True)

    # IDs for cleanup during deletion
    chroma_ids = Column(JSON, nullable=True)  # List of chunk IDs
    neo4j_node_ids = Column(JSON, nullable=True)  # List of node element IDs

    # Metadata
    file_size = Column(Integer, nullable=True)  # bytes
    chunk_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, name={self.name}, status={self.status})>"
