"""Document ingestion pipeline.
Handles Neo4j (GraphRAG) and ChromaDB (Vector) ingestion.
"""

import os

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from neo4j import GraphDatabase

from backend.config import settings
from backend.ingestion.loaders import load_confluence, load_document
from backend.models.db_models import (
    Document,
    DocumentType,
    Organization,
)
from backend.models.embeddings import get_embeddings
from backend.schema.boi_schema import get_schema_for_org


# Text splitter for chunking - using configurable settings
def get_text_splitter():
    """Get text splitter with configurable chunk size."""
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def get_chroma_client():
    """Get ChromaDB persistent client."""
    persist_dir = settings.chroma_persist_dir
    os.makedirs(persist_dir, exist_ok=True)
    return chromadb.PersistentClient(path=persist_dir)


def get_chroma_collection(org_id: int = None):
    """Get or create ChromaDB collection."""
    client = get_chroma_client()
    collection_name = f"org_{org_id}" if org_id else "default"
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )


def get_neo4j_driver():
    """Get Neo4j driver instance."""
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )


async def ingest_to_chroma(
    doc_id: int,
    file_path: str,
    doc_type: DocumentType,
    org_id: int,
) -> tuple[list[str], int]:
    """Ingest document to ChromaDB.

    Args:
        doc_id: Document ID for tracking
        file_path: Path to document
        doc_type: Type of document
        org_id: Organization ID

    Returns:
        Tuple of (chunk_ids, chunk_count)

    """
    # Load document
    if doc_type == DocumentType.CONFLUENCE:
        docs = load_confluence(file_path)  # file_path is URL for confluence
    else:
        docs = load_document(file_path, doc_type)

    # Split into chunks
    chunks = get_text_splitter().split_documents(docs)


    if not chunks:
        return [], 0

    # Get embeddings
    embedder = get_embeddings()
    texts = [chunk.page_content for chunk in chunks]
    embeddings = embedder.embed_documents(texts)

    # Prepare IDs and metadata
    chunk_ids = [f"doc_{doc_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "doc_id": doc_id,
            "org_id": org_id,
            "source": chunk.metadata.get("source", file_path),
            "page": chunk.metadata.get("page", 0),
            "chunk_index": i,
        }
        for i, chunk in enumerate(chunks)
    ]

    # Add to collection
    collection = get_chroma_collection(org_id)
    collection.add(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    return chunk_ids, len(chunks)


async def ingest_to_temp_collection(
    file_path: str,
    file_name: str,
    doc_type: DocumentType,
    temp_collection,
    expire_at: str,
) -> tuple[list[str], int]:
    """Ingest document to a temp ChromaDB collection.

    Reuses document loading and embedding logic from main ingestion.

    Args:
        file_path: Path to document file
        file_name: Original file name for metadata
        doc_type: Type of document
        temp_collection: ChromaDB collection to add to
        expire_at: ISO timestamp for expiration

    Returns:
        Tuple of (chunk_ids, chunk_count)
    """
    import hashlib
    from datetime import datetime

    # Load document - reuses existing loaders
    if doc_type == DocumentType.CONFLUENCE:
        docs = load_confluence(file_path)
    else:
        docs = load_document(file_path, doc_type)

    # Split into chunks
    chunks = get_text_splitter().split_documents(docs)

    if not chunks:
        return [], 0

    # Get embeddings - reuses existing embedder
    embedder = get_embeddings()
    texts = [chunk.page_content for chunk in chunks]
    embeddings = embedder.embed_documents(texts)

    # Prepare IDs and metadata for temp storage
    file_hash = hashlib.md5(file_name.encode()).hexdigest()[:8]
    chunk_ids = [f"temp_{file_hash}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source": file_name,
            "source_type": "file",
            "page": chunk.metadata.get("page", 0),
            "chunk_index": i,
            "expire_at": expire_at,
            "created_at": datetime.now().isoformat(),
        }
        for i, chunk in enumerate(chunks)
    ]

    # Add to temp collection
    temp_collection.add(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    print(f"📥 Ingested to temp: {file_name} ({len(chunks)} chunks)")
    return chunk_ids, len(chunks)


async def ingest_to_neo4j(
    doc_id: int,
    file_path: str,
    doc_type: DocumentType,
    org: Organization,
) -> list[str]:
    """Ingest document to Neo4j using LangChain's LLMGraphTransformer.

    This implementation:
    - Uses LLMGraphTransformer for entity extraction
    - Automatically tracks source documents with include_source=True
    - No manual Driver/Session management needed

    Args:
        doc_id: Document ID
        file_path: Path to document
        doc_type: Type of document
        org: Organization with schema config

    Returns:
        List of created node element IDs

    """
    try:
        from langchain_core.documents import (
            Document as LCDocument,  # noqa: F401
        )
        from langchain_experimental.graph_transformers import (
            LLMGraphTransformer,
        )
        from langchain_neo4j import Neo4jGraph
    except ImportError as err:
        raise ImportError(
            "langchain-experimental is required for GraphRAG ingestion"
        ) from err

    from backend.models.llm import get_langchain_llm

    # Get schema for organization
    schema = get_schema_for_org(org.graph_schema)

    # Load document
    if doc_type == DocumentType.CONFLUENCE:
        docs = load_confluence(file_path)
    else:
        docs = load_document(file_path, doc_type)

    # Split into chunks for better entity extraction
    chunks = get_text_splitter().split_documents(docs)


    if not chunks:
        return []

    # Add doc_id to metadata for each chunk
    for chunk in chunks:
        chunk.metadata["source_doc_id"] = doc_id
        chunk.metadata["org_id"] = org.id

    # Initialize Neo4jGraph (uses connection pooling internally)
    graph = Neo4jGraph(
        url=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )

    # Initialize transformer with schema constraints
    transformer = LLMGraphTransformer(
        llm=get_langchain_llm(),
        allowed_nodes=schema["node_types"],
        allowed_relationships=schema["relationship_types"],
    )

    try:
        # Convert documents to graph documents (entity extraction)
        graph_documents = transformer.convert_to_graph_documents(chunks)

        if not graph_documents:
            return []

        # Add to Neo4j with source tracking
        # include_source=True creates Document -> Entity relationships for citation
        graph.add_graph_documents(
            graph_documents,
            baseEntityLabel=True,  # Add base label for all entities
            include_source=True,   # Auto-create Document -> Entity relationships
        )

        # Query created nodes for this document
        result = graph.query(
            """
            MATCH (n)
            WHERE n.source_doc_id = $doc_id OR n.id CONTAINS $doc_id_str
            RETURN elementId(n) as id
            LIMIT 100
            """,
            {"doc_id": doc_id, "doc_id_str": str(doc_id)}
        )

        return [record["id"] for record in result]

    except Exception as e:
        print(f"Neo4j ingestion error: {e}")
        return []


async def ingest_document(
    doc: Document,
    org: Organization,
    update_status_callback=None,
) -> tuple[list[str], list[str], int]:
    """Full document ingestion pipeline.

    Args:
        doc: Document to ingest
        org: Organization the document belongs to
        update_status_callback: Optional callback to update status

    Returns:
        Tuple of (chroma_ids, neo4j_node_ids, chunk_count)

    """
    file_path = doc.source_url if doc.doc_type == DocumentType.CONFLUENCE else doc.file_path

    # Ingest to ChromaDB (always)
    chroma_ids, chunk_count = await ingest_to_chroma(
        doc_id=doc.id,
        file_path=file_path,
        doc_type=doc.doc_type,
        org_id=org.id,
    )

    neo4j_node_ids = []

    # Ingest to Neo4j if GraphRAG enabled
    if org.graphrag_enabled:
        neo4j_node_ids = await ingest_to_neo4j(
            doc_id=doc.id,
            file_path=file_path,
            doc_type=doc.doc_type,
            org=org,
        )

    return chroma_ids, neo4j_node_ids, chunk_count
