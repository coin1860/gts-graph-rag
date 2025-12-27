"""Temporary knowledge management for chat sessions.

Uses LangChain components for URL loading:
- AsyncHtmlLoader: Async HTML fetching
- BeautifulSoupTransformer: HTML cleaning and text extraction
- RecursiveCharacterTextSplitter: Text chunking

Handles:
- Temporary ChromaDB collections per session
- URL content fetching and embedding with expire_at metadata
- File embedding to temp collection
- Cleanup of expired sessions
"""

import hashlib
import os
import re
from datetime import datetime, timedelta

import chromadb
from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers import BeautifulSoupTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import settings
from backend.models.embeddings import get_embeddings

# Directory for temp data
TEMP_DIR = os.path.join(settings.chroma_persist_dir, "temp")

# Default expiration hours for temp data
DEFAULT_EXPIRE_HOURS = 24

# Tags to remove during HTML cleaning
UNWANTED_TAGS = ["nav", "footer", "header", "aside", "script", "style", "noscript"]


def get_temp_chroma_client():
    """Get ChromaDB client for temp collections."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=TEMP_DIR)


def get_temp_collection(session_id: str):
    """Get or create temp ChromaDB collection for session.

    Args:
        session_id: Unique session identifier (UUID from frontend)

    Returns:
        ChromaDB collection for this session
    """
    client = get_temp_chroma_client()
    collection_name = f"temp_{session_id[:32]}"  # Limit name length

    return client.get_or_create_collection(
        name=collection_name,
        metadata={
            "created_at": datetime.now().isoformat(),
            "session_id": session_id,
            "hnsw:space": "cosine",
        }
    )


def extract_urls_from_text(text: str) -> list[str]:
    """Extract URLs from text using regex.

    Args:
        text: Input text to search for URLs

    Returns:
        List of found URLs
    """
    url_pattern = r"https?://[^\s<>\"')\]]+|www\.[^\s<>\"')\]]+"
    urls = re.findall(url_pattern, text)

    # Clean trailing punctuation
    cleaned = []
    for url in urls:
        url = url.rstrip(".,;:!?")
        if url.startswith("www."):
            url = "https://" + url
        cleaned.append(url)

    return list(set(cleaned))


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """Get text splitter with configurable chunk settings."""
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


async def load_urls_with_langchain(urls: list[str]) -> list[dict]:
    """Load and transform URLs using LangChain AsyncHtmlLoader.

    Uses:
    - AsyncHtmlLoader for async HTTP fetching
    - BeautifulSoupTransformer for HTML cleaning

    Args:
        urls: List of URLs to load

    Returns:
        List of cleaned document dicts with content and metadata
    """
    if not urls:
        return []

    results = []

    try:
        # Step 1: Load HTML content asynchronously
        loader = AsyncHtmlLoader(urls)
        html_docs = await loader.aload()

        if not html_docs:
            return []

        # Step 2: Transform HTML - extract body text, remove noise
        bs_transformer = BeautifulSoupTransformer()
        docs_transformed = bs_transformer.transform_documents(
            html_docs,
            tags_to_extract=["body"],
            unwanted_tags=UNWANTED_TAGS,
            remove_comments=True,
        )

        # Convert to dict format
        for doc in docs_transformed:
            content = doc.page_content.strip()
            if len(content) > 50:  # Skip empty/tiny pages
                results.append({
                    "content": content,
                    "source": doc.metadata.get("source", "unknown"),
                    "title": doc.metadata.get("title", ""),
                })

    except Exception as e:
        print(f"⚠️ Error loading URLs: {e}")

    return results


async def ingest_urls_to_temp(
    session_id: str,
    urls: list[str],
    expire_hours: int = DEFAULT_EXPIRE_HOURS,
) -> tuple[list[str], int]:
    """Load URLs and embed to temp collection using LangChain.

    Args:
        session_id: Session identifier
        urls: List of URLs to fetch and embed
        expire_hours: Hours until expiration (default 24)

    Returns:
        Tuple of (list of chunk IDs, total content length)
    """
    if not urls:
        return [], 0

    # Load and transform URLs
    url_docs = await load_urls_with_langchain(urls)

    if not url_docs:
        return [], 0

    # Combine all content
    all_chunks = []
    chunk_metadata = []

    splitter = get_text_splitter()
    expire_at = (datetime.now() + timedelta(hours=expire_hours)).isoformat()

    for doc in url_docs:
        content = doc["content"]
        source = doc["source"]

        # Split content into chunks
        chunks = splitter.split_text(content)

        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            chunk_metadata.append({
                "source": source,
                "source_type": "url",
                "chunk_index": i,
                "expire_at": expire_at,
                "created_at": datetime.now().isoformat(),
            })

    if not all_chunks:
        return [], 0

    # Get embeddings
    embeddings = get_embeddings()
    vectors = embeddings.embed_documents(all_chunks)

    # Generate IDs with URL hash
    url_hash = hashlib.md5("".join(urls).encode()).hexdigest()[:8]
    ids = [f"url_{url_hash}_{i}" for i in range(len(all_chunks))]

    # Add to temp collection
    collection = get_temp_collection(session_id)
    collection.add(
        ids=ids,
        embeddings=vectors,
        documents=all_chunks,
        metadatas=chunk_metadata
    )

    total_content = sum(len(doc["content"]) for doc in url_docs)
    print(
        f"📥 Ingested {len(urls)} URL(s) to temp: "
        f"{len(all_chunks)} chunks, {total_content} chars"
    )

    return ids, total_content


async def ingest_url_to_temp(
    session_id: str,
    url: str,
    expire_hours: int = DEFAULT_EXPIRE_HOURS,
) -> list[str]:
    """Fetch single URL content and embed to temp collection.

    Wrapper for ingest_urls_to_temp for single URL.

    Args:
        session_id: Session identifier
        url: URL to fetch and embed
        expire_hours: Hours until expiration

    Returns:
        List of created chunk IDs
    """
    ids, _ = await ingest_urls_to_temp(session_id, [url], expire_hours)
    return ids


async def ingest_file_to_temp(
    session_id: str,
    file_path: str,
    file_name: str,
    expire_hours: int = DEFAULT_EXPIRE_HOURS,
) -> list[str]:
    """Embed uploaded file to temp collection.

    Reuses the main ingestion logic from ingest.py for document loading
    and embedding.

    Args:
        session_id: Session identifier
        file_path: Path to uploaded file
        file_name: Original file name
        expire_hours: Hours until expiration

    Returns:
        List of created chunk IDs
    """
    from backend.ingestion.ingest import ingest_to_temp_collection
    from backend.models.db_models import DocumentType

    # Determine doc type from extension
    ext = os.path.splitext(file_name)[1].lower()
    type_map = {
        ".pdf": DocumentType.PDF,
        ".md": DocumentType.MARKDOWN,
        ".txt": DocumentType.TXT,
        ".docx": DocumentType.DOCX,
        ".xlsx": DocumentType.XLSX,
        ".html": DocumentType.HTML,
    }
    doc_type = type_map.get(ext, DocumentType.TXT)

    # Calculate expiration time
    expire_at = (datetime.now() + timedelta(hours=expire_hours)).isoformat()

    # Get temp collection for this session
    collection = get_temp_collection(session_id)

    # Reuse main ingestion logic
    chunk_ids, _ = await ingest_to_temp_collection(
        file_path=file_path,
        file_name=file_name,
        doc_type=doc_type,
        temp_collection=collection,
        expire_at=expire_at,
    )

    return chunk_ids


def has_temp_data(session_id: str) -> bool:
    """Check if session has any temp data.

    Args:
        session_id: Session identifier

    Returns:
        True if temp collection exists and has data
    """
    try:
        collection = get_temp_collection(session_id)
        return collection.count() > 0
    except Exception:
        return False


def cleanup_expired_sessions(max_age_hours: int = DEFAULT_EXPIRE_HOURS) -> int:
    """Delete temp collections older than max_age.

    Checks both collection metadata and individual document expire_at.

    Args:
        max_age_hours: Maximum age in hours

    Returns:
        Number of deleted collections
    """
    client = get_temp_chroma_client()
    collections = client.list_collections()
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    deleted = 0

    for coll in collections:
        if not coll.name.startswith("temp_"):
            continue

        try:
            metadata = coll.metadata or {}
            created_str = metadata.get("created_at")
            if created_str:
                created = datetime.fromisoformat(created_str)
                if created < cutoff:
                    client.delete_collection(coll.name)
                    deleted += 1
                    print(f"🗑️ Deleted expired temp: {coll.name}")
        except Exception as e:
            print(f"⚠️ Error checking collection {coll.name}: {e}")

    return deleted


def cleanup_expired_documents(session_id: str) -> int:
    """Delete expired documents within a session's temp collection.

    Checks expire_at metadata on individual documents.

    Args:
        session_id: Session identifier

    Returns:
        Number of deleted documents
    """
    try:
        collection = get_temp_collection(session_id)
        now = datetime.now()

        # Get all documents with metadata
        results = collection.get(include=["metadatas"])
        if not results or not results["ids"]:
            return 0

        expired_ids = []
        for i, doc_id in enumerate(results["ids"]):
            meta = results["metadatas"][i] if results["metadatas"] else {}
            expire_str = meta.get("expire_at")
            if expire_str:
                try:
                    expire_at = datetime.fromisoformat(expire_str)
                    if expire_at < now:
                        expired_ids.append(doc_id)
                except ValueError:
                    pass

        if expired_ids:
            collection.delete(ids=expired_ids)
            print(f"🗑️ Deleted {len(expired_ids)} expired docs from {session_id}")

        return len(expired_ids)

    except Exception as e:
        print(f"⚠️ Error cleaning expired docs: {e}")
        return 0


def cleanup_session(session_id: str) -> bool:
    """Delete temp collection for specific session.

    Args:
        session_id: Session identifier

    Returns:
        True if deleted successfully
    """
    try:
        client = get_temp_chroma_client()
        collection_name = f"temp_{session_id[:32]}"
        client.delete_collection(collection_name)
        print(f"🗑️ Deleted temp collection: {collection_name}")
        return True
    except Exception as e:
        print(f"⚠️ Failed to delete temp: {e}")
        return False


def calculate_extraction_rate(
    original_html_length: int,
    extracted_text_length: int
) -> float:
    """Calculate content extraction rate.

    Args:
        original_html_length: Length of original HTML
        extracted_text_length: Length of extracted text

    Returns:
        Extraction rate as percentage (0-100)
    """
    if original_html_length == 0:
        return 0.0
    return (extracted_text_length / original_html_length) * 100
