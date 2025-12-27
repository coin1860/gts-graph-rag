"""Cleanup utilities for deleting document data from Neo4j and ChromaDB.
Ensures sync deletion when documents are removed.
"""

import os

from backend.config import settings
from backend.ingestion.ingest import get_chroma_collection, get_neo4j_driver
from backend.models.db_models import Document


async def delete_from_chroma(
    doc: Document,
    org_id: int | None = None,
) -> int:
    """Delete document chunks from ChromaDB.

    Args:
        doc: Document with chroma_ids
        org_id: Organization ID for collection

    Returns:
        Number of chunks deleted

    """
    if not doc.chroma_ids:
        return 0

    collection = get_chroma_collection(org_id or doc.org_id)

    try:
        collection.delete(ids=doc.chroma_ids)
        return len(doc.chroma_ids)
    except Exception as e:
        # Log error but don't fail
        print(f"Warning: Failed to delete from ChromaDB: {e}")
        return 0


async def delete_from_neo4j(
    doc: Document,
) -> int:
    """Delete document nodes and relationships from Neo4j.

    Args:
        doc: Document with neo4j_node_ids

    Returns:
        Number of nodes deleted

    """
    if not doc.neo4j_node_ids:
        return 0

    driver = get_neo4j_driver()

    try:
        with driver.session(database=settings.neo4j_database) as session:
            # Delete nodes and their relationships
            result = session.run(
                """
                MATCH (n)
                WHERE elementId(n) IN $ids
                DETACH DELETE n
                RETURN count(n) as deleted
                """,
                ids=doc.neo4j_node_ids
            )
            deleted = result.single()["deleted"]
            return deleted
    except Exception as e:
        print(f"Warning: Failed to delete from Neo4j: {e}")
        return 0
    finally:
        driver.close()


def delete_file(file_path: str | None) -> bool:
    """Delete the physical file from disk.

    Args:
        file_path: Path to the file

    Returns:
        True if deleted, False otherwise

    """
    if not file_path:
        return False

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        print(f"Warning: Failed to delete file: {e}")

    return False


async def delete_document_data(
    doc: Document,
    delete_file_on_disk: bool = True,
) -> dict:
    """Full cleanup: delete document data from all storage.

    Args:
        doc: Document to clean up
        delete_file_on_disk: Whether to delete physical file

    Returns:
        Dict with deletion stats

    """
    stats = {
        "chroma_deleted": 0,
        "neo4j_deleted": 0,
        "file_deleted": False,
    }

    # Delete from ChromaDB
    stats["chroma_deleted"] = await delete_from_chroma(doc)

    # Delete from Neo4j
    stats["neo4j_deleted"] = await delete_from_neo4j(doc)

    # Delete physical file
    if delete_file_on_disk:
        stats["file_deleted"] = delete_file(doc.file_path)

    return stats
