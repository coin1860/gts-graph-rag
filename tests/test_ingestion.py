"""Unit tests for document ingestion.

Tests cover:
- Document loading for various file types
- ChromaDB ingestion
- Text chunking
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


class TestDocumentLoaders:
    """Tests for document loaders."""

    @pytest.mark.parametrize("file_type,content", [
        ("md", "# Test Markdown\n\nThis is test content."),
        ("txt", "Plain text content for testing."),
    ])
    def test_load_text_files(self, tmp_path, file_type, content):
        """Test loading text-based files."""
        from backend.ingestion.loaders import load_document
        from backend.models.db_models import DocumentType
        
        # Create test file
        test_file = tmp_path / f"test.{file_type}"
        test_file.write_text(content)
        
        doc_type = DocumentType.MARKDOWN if file_type == "md" else DocumentType.TXT
        
        docs = load_document(str(test_file), doc_type)
        
        assert len(docs) > 0
        assert content in docs[0].page_content

    def test_load_nonexistent_file(self):
        """Test handling of nonexistent file."""
        from backend.ingestion.loaders import load_document
        from backend.models.db_models import DocumentType
        
        with pytest.raises(Exception):
            load_document("/nonexistent/path.pdf", DocumentType.PDF)


class TestTextSplitter:
    """Tests for text chunking."""

    def test_chunk_creation(self):
        """Test that text is properly chunked."""
        from backend.ingestion.ingest import get_text_splitter
        from langchain_core.documents import Document
        
        splitter = get_text_splitter()
        
        # Create a long document
        long_text = "This is a test sentence. " * 100
        docs = [Document(page_content=long_text)]
        
        chunks = splitter.split_documents(docs)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.page_content) > 0

    def test_chunk_overlap(self):
        """Test that chunks have proper overlap."""
        from backend.ingestion.ingest import get_text_splitter
        from langchain_core.documents import Document
        
        splitter = get_text_splitter()
        
        long_text = "Word " * 500
        docs = [Document(page_content=long_text)]
        
        chunks = splitter.split_documents(docs)
        
        # With overlap, consecutive chunks should share some content
        if len(chunks) > 1:
            chunk1_end = chunks[0].page_content[-50:]
            chunk2_start = chunks[1].page_content[:100]
            # Some overlap expected
            assert len(set(chunk1_end.split()) & set(chunk2_start.split())) > 0


class TestChromaIngestion:
    """Tests for ChromaDB ingestion."""

    @patch("backend.ingestion.ingest.get_chroma_collection")
    @patch("backend.ingestion.ingest.get_embeddings")
    @patch("backend.ingestion.ingest.load_document")
    async def test_ingest_to_chroma(
        self,
        mock_load_doc,
        mock_get_embeddings,
        mock_get_collection,
        mock_embeddings,
        mock_chroma_collection,
    ):
        """Test successful ingestion to ChromaDB."""
        from backend.ingestion.ingest import ingest_to_chroma
        from backend.models.db_models import DocumentType
        from langchain_core.documents import Document
        
        mock_load_doc.return_value = [
            Document(
                page_content="Test content for ingestion.",
                metadata={"source": "test.pdf"}
            )
        ]
        mock_get_embeddings.return_value = mock_embeddings
        mock_get_collection.return_value = mock_chroma_collection
        
        chunk_ids, count = await ingest_to_chroma(
            doc_id=1,
            file_path="/fake/path.pdf",
            doc_type=DocumentType.PDF,
            org_id=1,
        )
        
        assert isinstance(chunk_ids, list)
        mock_chroma_collection.add.assert_called()

    @patch("backend.ingestion.ingest.get_chroma_collection")
    @patch("backend.ingestion.ingest.get_embeddings")
    @patch("backend.ingestion.ingest.load_document")
    async def test_ingest_empty_document(
        self,
        mock_load_doc,
        mock_get_embeddings,
        mock_get_collection,
        mock_embeddings,
        mock_chroma_collection,
    ):
        """Test handling of empty document."""
        from backend.ingestion.ingest import ingest_to_chroma
        from backend.models.db_models import DocumentType
        
        mock_load_doc.return_value = []
        mock_get_embeddings.return_value = mock_embeddings
        mock_get_collection.return_value = mock_chroma_collection
        
        chunk_ids, count = await ingest_to_chroma(
            doc_id=1,
            file_path="/fake/empty.pdf",
            doc_type=DocumentType.PDF,
            org_id=1,
        )
        
        assert chunk_ids == []
        assert count == 0


class TestChromaCleanup:
    """Tests for ChromaDB cleanup operations."""

    @patch("backend.ingestion.cleanup.get_chroma_collection")
    def test_delete_document_chunks(self, mock_get_collection):
        """Test deletion of document chunks from ChromaDB."""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": ["chunk1", "chunk2"]}
        mock_get_collection.return_value = mock_collection
        
        from backend.ingestion.cleanup import delete_document_from_chroma
        
        delete_document_from_chroma(doc_id=1, org_id=1)
        
        mock_collection.delete.assert_called_once()
