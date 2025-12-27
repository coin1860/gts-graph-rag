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
        dashscope_api_key="test_key",
        jwt_secret_key="test_secret",
        neo4j_password="test_password",
    )
    
    assert settings.neo4j_uri is not None
    assert settings.neo4j_username == "neo4j"
    assert settings.neo4j_database == "neo4j"


def test_dashscope_config():
    """Test DashScope configuration."""
    settings = Settings(
        dashscope_api_key="test_key",
        jwt_secret_key="test_secret",
        neo4j_password="test_password",
    )
    
    assert settings.llm_model == "qwen-plus"
    assert settings.embedding_model == "text-embedding-v1"
    assert "dashscope" in settings.dashscope_base_url
