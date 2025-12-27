"""Ingestion package - Document loading and processing."""

from backend.ingestion.cleanup import (
    delete_document_data,
    delete_from_chroma,
    delete_from_neo4j,
)
from backend.ingestion.ingest import (
    ingest_document,
    ingest_to_chroma,
    ingest_to_neo4j,
)
from backend.ingestion.loaders import (
    get_loader_for_type,
    load_confluence,
    load_document,
)

__all__ = [
    # Loaders
    "load_document",
    "load_confluence",
    "get_loader_for_type",
    # Ingestion
    "ingest_document",
    "ingest_to_chroma",
    "ingest_to_neo4j",
    # Cleanup
    "delete_document_data",
    "delete_from_chroma",
    "delete_from_neo4j",
]
