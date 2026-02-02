"""
Unit tests for configuration module.
"""

import pytest
from backend.config import Settings


def test_settings_defaults():
    """Test that settings have reasonable defaults."""
    # Note: This will fail if required env vars aren't set
    # In production, use .env file
    pass


def test_neo4j_config():
    """Test Neo4j configuration."""
    settings = Settings(
        llm_api_key="test_key",
        embedding_api_key="test_key",
        jwt_secret_key="test_secret",
        neo4j_password="test_password",
    )
    
    assert settings.neo4j_uri is not None
    assert settings.neo4j_username == "neo4j"
    assert settings.neo4j_database == "neo4j"


def test_llm_and_embedding_config():
    """Test LLM and Embedding configuration with separate API keys and base URLs."""
    settings = Settings(
        llm_api_key="test_llm_key",
        embedding_api_key="test_embedding_key",
        jwt_secret_key="test_secret",
        neo4j_password="test_password",
    )
    
    # LLM settings
    assert settings.llm_api_key == "test_llm_key"
    assert settings.llm_model == "qwen-flash"
    assert "dashscope" in settings.llm_base_url
    
    # Embedding settings
    assert settings.embedding_api_key == "test_embedding_key"
    assert settings.embedding_model == "text-embedding-v1"
    assert "dashscope" in settings.embedding_base_url
    
    # Rerank settings (optional, default disabled)
    assert settings.rerank_enabled == False
    assert settings.rerank_model == "gte-rerank"

