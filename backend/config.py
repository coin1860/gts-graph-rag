"""Configuration module for the GTS Graph RAG system.
Uses Pydantic Settings for environment variable management.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # DashScope (Qwen-Plus & Embeddings)
    dashscope_api_key: str = Field(..., env="DASHSCOPE_API_KEY")
    dashscope_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        env="DASHSCOPE_BASE_URL"
    )
    llm_model: str = Field(default="qwen-flash", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")
    embedding_model: str = Field(default="text-embedding-v1", env="EMBEDDING_MODEL")
    rerank_model: str = Field(default="gte-rerank", env="RERANK_MODEL")

    # Neo4j
    neo4j_uri: str = Field(default="neo4j://localhost:7687", env="NEO4J_URI")
    neo4j_username: str = Field(default="neo4j", env="NEO4J_USERNAME")
    neo4j_password: str = Field(..., env="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", env="NEO4J_DATABASE")

    # ChromaDB
    chroma_persist_dir: str = Field(default="./data/chroma", env="CHROMA_PERSIST_DIR")

    # SQLite Database
    database_url: str = Field(default="sqlite:///./data/app.db", env="DATABASE_URL")

    # JWT Authentication
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_hours: int = Field(default=8, env="JWT_EXPIRE_HOURS")

    # Server
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    cors_origins: list[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")

    # File Upload
    upload_dir: str = Field(default="./data/uploads", env="UPLOAD_DIR")
    max_upload_size_mb: int = Field(default=50, env="MAX_UPLOAD_SIZE_MB")

    # RAG Settings
    min_relevance_score: float = Field(default=0.3, env="MIN_RELEVANCE_SCORE")
    vector_search_results: int = Field(default=5, env="VECTOR_SEARCH_RESULTS")

    # Document Chunking
    chunk_size: int = Field(default=500, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=100, env="CHUNK_OVERLAP")

    # Prompt Templates
    grader_prompt: str = Field(
        default="""Evaluate if the following context contains ANY information related to the question.
Answer 'YES' if the context mentions the topic or contains partial information that could help answer the question.
Answer 'NO' only if the context is completely unrelated to the question.

Question: {question}

Context:
{context}

Your answer (YES or NO):""",
        env="GRADER_PROMPT"
    )

    generator_system_prompt: str = Field(
        default="You are an expert technical assistant for the HSBC BOI (Back Office Integration) system. Answer questions based on the provided context. Be accurate and cite sources when possible. If the context doesn't contain enough information, say so clearly.",
        env="GENERATOR_SYSTEM_PROMPT"
    )
    generator_user_prompt: str = Field(
        default="Question: {question}\n\nContext:\n{context}\n\nPlease provide a comprehensive answer based on the context above. Include relevant citations.",
        env="GENERATOR_USER_PROMPT"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience function for accessing settings
settings = get_settings()
