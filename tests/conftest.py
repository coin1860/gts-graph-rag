"""Shared pytest fixtures for all tests.

Provides mock implementations for:
- Database sessions
- Neo4j connections
- LLM interfaces
- ChromaDB clients
"""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.db_models import User, Organization, UserRole


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_user(test_db):
    """Create a sample admin user for testing."""
    user = User(
        username="testadmin",
        email="admin@test.com",
        hashed_password="hashedpass",
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_org(test_db):
    """Create a sample organization for testing."""
    org = Organization(
        name="Test Org",
        description="Test organization",
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)
    return org


# =============================================================================
# Neo4j Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_neo4j_graph():
    """Mock Neo4jGraph for testing graph operations."""
    mock_graph = MagicMock()
    mock_graph.query.return_value = [
        {"n": {"id": "TestEntity1"}},
        {"n": {"id": "TestEntity2"}},
    ]
    mock_graph.schema = "Node properties:\nTest {id: STRING}"
    return mock_graph


@pytest.fixture
def mock_cypher_chain(mock_neo4j_graph):
    """Mock GraphCypherQAChain for testing."""
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = {
        "result": "Test answer from graph",
        "intermediate_steps": [{"query": "MATCH (n) RETURN n"}],
    }
    return mock_chain


# =============================================================================
# LLM Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_llm():
    """Mock LLM for testing generation."""
    mock = MagicMock()
    mock.invoke.return_value = MagicMock(content="Mocked LLM response")
    return mock


@pytest.fixture
def mock_embeddings():
    """Mock embeddings model for testing."""
    mock = MagicMock()
    mock.embed_documents.return_value = [[0.1] * 768]
    mock.embed_query.return_value = [0.1] * 768
    return mock


# =============================================================================
# ChromaDB Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_chroma_collection():
    """Mock ChromaDB collection for testing."""
    mock = MagicMock()
    mock.query.return_value = {
        "ids": [["doc1", "doc2"]],
        "documents": [["Test content 1", "Test content 2"]],
        "metadatas": [[{"source": "test.pdf"}, {"source": "test2.pdf"}]],
        "distances": [[0.1, 0.2]],
    }
    mock.add.return_value = None
    return mock


# =============================================================================
# FastAPI Test Client Fixtures
# =============================================================================


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient
    from backend.server import app
    from backend.database import get_db
    
    # Override database dependency
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    
    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(sample_user):
    """Generate valid JWT auth headers for testing."""
    from backend.auth.jwt import create_access_token
    
    token = create_access_token({"sub": sample_user.username})
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Agent State Fixtures
# =============================================================================


@pytest.fixture
def sample_agent_state():
    """Create a sample agent state for testing nodes."""
    return {
        "question": "What is BOI?",
        "org_ids": [1],
        "selected_files": [],
        "vector_context": [],
        "graph_context": [],
        "context": [],
        "answer": "",
        "steps": [],
        "is_sufficient": None,
        "graph_viz_data": None,
    }


@pytest.fixture
def sample_context():
    """Sample retrieved context for testing."""
    return [
        {
            "content": "BOI is the Back Office Integration system.",
            "source": "test.pdf",
            "score": 0.95,
            "metadata": {"page": 1},
        },
        {
            "content": "BOI handles transaction processing.",
            "source": "test2.pdf",
            "score": 0.85,
            "metadata": {"page": 5},
        },
    ]
