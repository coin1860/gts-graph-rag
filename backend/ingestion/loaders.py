"""Multi-format document loaders for ingestion.
Supports PDF, TXT, HTML, and Confluence links.
"""

import os

from langchain_community.document_loaders import (
    PyMuPDFLoader,
    TextLoader,
    UnstructuredExcelLoader,
    UnstructuredHTMLLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_core.documents import Document as LangchainDocument

from backend.models.db_models import DocumentType


def get_loader_for_type(file_path: str, doc_type: DocumentType):
    """Get the appropriate loader for a document type.

    Args:
        file_path: Path to the document file
        doc_type: Type of document

    Returns:
        Document loader instance

    """
    loaders = {
        DocumentType.PDF: PyMuPDFLoader,
        DocumentType.TXT: TextLoader,
        DocumentType.MARKDOWN: TextLoader,  # Markdown files use TextLoader
        DocumentType.HTML: UnstructuredHTMLLoader,
        DocumentType.DOCX: UnstructuredWordDocumentLoader,
        DocumentType.XLSX: UnstructuredExcelLoader,
    }

    loader_class = loaders.get(doc_type)
    if not loader_class:
        raise ValueError(f"No loader available for document type: {doc_type}")

    return loader_class(file_path)


def load_document(file_path: str, doc_type: DocumentType) -> list[LangchainDocument]:
    """Load a document from file.

    Args:
        file_path: Path to the document file
        doc_type: Type of document

    Returns:
        List of LangChain Document objects

    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Document not found: {file_path}")

    loader = get_loader_for_type(file_path, doc_type)
    return loader.load()


def load_confluence(
    page_url: str,
    api_key: str | None = None,
    username: str | None = None,
) -> list[LangchainDocument]:
    """Load content from a Confluence page.

    Args:
        page_url: URL of the Confluence page
        api_key: Confluence API key
        username: Confluence username

    Returns:
        List of LangChain Document objects

    """
    # For now, use basic HTTP fetch. Can be upgraded to official Confluence API later.
    # This is a placeholder implementation.
    import requests
    from bs4 import BeautifulSoup

    try:
        headers = {}
        if api_key and username:
            import base64
            auth_str = base64.b64encode(f"{username}:{api_key}".encode()).decode()
            headers["Authorization"] = f"Basic {auth_str}"

        response = requests.get(page_url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract main content
        content = soup.get_text(separator="\n", strip=True)
        title = soup.title.string if soup.title else "Confluence Page"

        return [
            LangchainDocument(
                page_content=content,
                metadata={
                    "source": page_url,
                    "title": title,
                    "type": "confluence",
                }
            )
        ]
    except Exception as e:
        raise RuntimeError(f"Failed to load Confluence page: {e}") from e



def extract_text_from_file(file_path: str, doc_type: DocumentType) -> str:
    """Extract plain text from a document.

    Args:
        file_path: Path to the document
        doc_type: Type of document

    Returns:
        Extracted text content

    """
    docs = load_document(file_path, doc_type)
    return "\n\n".join(doc.page_content for doc in docs)
