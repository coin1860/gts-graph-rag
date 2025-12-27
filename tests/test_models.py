"""
Unit tests for database models.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models.db_models import Organization, User, Document, UserRole, DocumentStatus, DocumentType


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()


def test_create_organization(test_db):
    """Test creating an organization."""
    org = Organization(
        name="Test Org",
        description="Test Description",
        graphrag_enabled=True
    )
    test_db.add(org)
    test_db.commit()
    
    assert org.id is not None
    assert org.name == "Test Org"
    assert org.graphrag_enabled is True


def test_create_user(test_db):
    """Test creating a user."""
    user = User(
        username="testuser",
        password_hash="hashed_password",
        role=UserRole.USER,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    
    assert user.id is not None
    assert user.username == "testuser"
    assert user.role == UserRole.USER


def test_user_organization_relationship(test_db):
    """Test user-organization many-to-many relationship."""
    org = Organization(name="Test Org")
    user = User(username="testuser", password_hash="hash", role=UserRole.USER)
    
    user.organizations.append(org)
    test_db.add(user)
    test_db.commit()
    
    assert len(user.organizations) == 1
    assert user.organizations[0].name == "Test Org"


def test_create_document(test_db):
    """Test creating a document."""
    org = Organization(name="Test Org")
    test_db.add(org)
    test_db.commit()
    
    doc = Document(
        name="test.pdf",
        doc_type=DocumentType.PDF,
        org_id=org.id,
        status=DocumentStatus.PENDING,
        file_path="/path/to/test.pdf"
    )
    test_db.add(doc)
    test_db.commit()
    
    assert doc.id is not None
    assert doc.name == "test.pdf"
    assert doc.status == DocumentStatus.PENDING
    assert doc.org_id == org.id
