"""Unit tests for temporary knowledge URL loading.

Tests cover:
- URL extraction from text
- AsyncHtmlLoader mocking
- BeautifulSoupTransformer content extraction
- Extraction rate calculation
- expire_at metadata handling
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document


class TestUrlExtraction:
    """Tests for URL extraction from text."""

    @pytest.mark.parametrize("text,expected_count", [
        ("Check https://example.com", 1),
        ("Visit www.test.org for info", 1),
        ("No URLs here", 0),
        ("Multiple: https://a.com and https://b.com", 2),
        ("URL with trailing: https://example.com.", 1),
        ("URL in parens (https://example.com)", 1),
        ("", 0),
    ])
    def test_extract_urls_count(self, text, expected_count):
        """Test URL extraction counts."""
        from backend.ingestion.temp_knowledge import extract_urls_from_text

        urls = extract_urls_from_text(text)
        assert len(urls) == expected_count

    def test_extract_urls_cleans_trailing_punctuation(self):
        """Test that trailing punctuation is removed from URLs."""
        from backend.ingestion.temp_knowledge import extract_urls_from_text

        text = "Check https://example.com/path. And https://test.org!"
        urls = extract_urls_from_text(text)

        assert "https://example.com/path" in urls
        assert "https://test.org" in urls
        # Should not have punctuation
        assert not any(u.endswith(".") or u.endswith("!") for u in urls)

    def test_extract_urls_adds_https_to_www(self):
        """Test that www URLs get https:// prefix."""
        from backend.ingestion.temp_knowledge import extract_urls_from_text

        urls = extract_urls_from_text("Visit www.example.com")
        assert "https://www.example.com" in urls

    def test_extract_urls_deduplicates(self):
        """Test that duplicate URLs are removed."""
        from backend.ingestion.temp_knowledge import extract_urls_from_text

        text = "https://example.com and https://example.com again"
        urls = extract_urls_from_text(text)

        assert len(urls) == 1


class TestExtractionRate:
    """Tests for extraction rate calculation."""

    def test_extraction_rate_calculation(self):
        """Test extraction rate percentage."""
        from backend.ingestion.temp_knowledge import calculate_extraction_rate

        rate = calculate_extraction_rate(1000, 500)
        assert rate == 50.0

    def test_extraction_rate_zero_html(self):
        """Test extraction rate with zero HTML length."""
        from backend.ingestion.temp_knowledge import calculate_extraction_rate

        rate = calculate_extraction_rate(0, 100)
        assert rate == 0.0

    @pytest.mark.parametrize("html_len,text_len,expected", [
        (1000, 500, 50.0),
        (1000, 1000, 100.0),
        (1000, 0, 0.0),
        (100, 50, 50.0),
    ])
    def test_extraction_rate_parametrized(self, html_len, text_len, expected):
        """Parametrized extraction rate tests."""
        from backend.ingestion.temp_knowledge import calculate_extraction_rate

        rate = calculate_extraction_rate(html_len, text_len)
        assert rate == expected


class TestHtmlLoading:
    """Tests for HTML loading with mocked network."""

    @pytest.mark.asyncio
    @patch("backend.ingestion.temp_knowledge.AsyncHtmlLoader")
    async def test_load_urls_with_langchain(self, mock_loader_class):
        """Test URL loading with mocked AsyncHtmlLoader."""
        from backend.ingestion.temp_knowledge import load_urls_with_langchain

        # Mock HTML document
        mock_doc = Document(
            page_content="<html><body><p>Test content</p></body></html>",
            metadata={"source": "https://example.com"}
        )

        mock_loader = MagicMock()
        mock_loader.aload = AsyncMock(return_value=[mock_doc])
        mock_loader_class.return_value = mock_loader

        # Patch BeautifulSoupTransformer
        with patch(
            "backend.ingestion.temp_knowledge.BeautifulSoupTransformer"
        ) as mock_bs:
            mock_transformer = MagicMock()
            # Content must be > 50 chars to pass filter
            long_content = (
                "Test content extracted from webpage. "
                "This is additional text to meet the minimum length."
            )
            transformed_doc = Document(
                page_content=long_content,
                metadata={"source": "https://example.com", "title": "Test"}
            )
            mock_transformer.transform_documents.return_value = [transformed_doc]
            mock_bs.return_value = mock_transformer

            result = await load_urls_with_langchain(["https://example.com"])

        assert len(result) == 1
        assert "Test content extracted" in result[0]["content"]
        assert result[0]["source"] == "https://example.com"

    @pytest.mark.asyncio
    @patch("backend.ingestion.temp_knowledge.AsyncHtmlLoader")
    async def test_load_urls_empty_content_filtered(self, mock_loader_class):
        """Test that empty/tiny content is filtered out."""
        from backend.ingestion.temp_knowledge import load_urls_with_langchain

        mock_loader = MagicMock()
        mock_loader.aload = AsyncMock(return_value=[])
        mock_loader_class.return_value = mock_loader

        result = await load_urls_with_langchain(["https://example.com"])
        assert result == []

    @pytest.mark.asyncio
    @patch("backend.ingestion.temp_knowledge.AsyncHtmlLoader")
    async def test_load_urls_handles_exception(self, mock_loader_class):
        """Test graceful error handling."""
        from backend.ingestion.temp_knowledge import load_urls_with_langchain

        mock_loader = MagicMock()
        mock_loader.aload = AsyncMock(side_effect=Exception("Network error"))
        mock_loader_class.return_value = mock_loader

        result = await load_urls_with_langchain(["https://example.com"])
        assert result == []


class TestTempIngestion:
    """Tests for temp collection ingestion."""

    @pytest.mark.asyncio
    @patch("backend.ingestion.temp_knowledge.get_embeddings")
    @patch("backend.ingestion.temp_knowledge.get_temp_collection")
    @patch("backend.ingestion.temp_knowledge.load_urls_with_langchain")
    async def test_ingest_urls_to_temp(
        self,
        mock_load_urls,
        mock_get_collection,
        mock_get_embeddings,
    ):
        """Test URL ingestion to temp collection."""
        from backend.ingestion.temp_knowledge import ingest_urls_to_temp

        # Mock URL loading
        mock_load_urls.return_value = [{
            "content": "This is test content from the URL. " * 10,
            "source": "https://example.com",
            "title": "Test Page",
        }]

        # Mock embeddings
        mock_embeddings = MagicMock()
        mock_embeddings.embed_documents.return_value = [[0.1] * 768]
        mock_get_embeddings.return_value = mock_embeddings

        # Mock collection
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        chunk_ids, total_chars = await ingest_urls_to_temp(
            session_id="test-session-123",
            urls=["https://example.com"],
        )

        assert len(chunk_ids) > 0
        assert total_chars > 0
        mock_collection.add.assert_called_once()

    @pytest.mark.asyncio
    @patch("backend.ingestion.temp_knowledge.load_urls_with_langchain")
    async def test_ingest_urls_empty_result(self, mock_load_urls):
        """Test ingestion with no content."""
        from backend.ingestion.temp_knowledge import ingest_urls_to_temp

        mock_load_urls.return_value = []

        chunk_ids, total_chars = await ingest_urls_to_temp(
            session_id="test-session-123",
            urls=["https://example.com"],
        )

        assert chunk_ids == []
        assert total_chars == 0


class TestExpireAtMetadata:
    """Tests for expire_at metadata handling."""

    @pytest.mark.asyncio
    @patch("backend.ingestion.temp_knowledge.get_embeddings")
    @patch("backend.ingestion.temp_knowledge.get_temp_collection")
    @patch("backend.ingestion.temp_knowledge.load_urls_with_langchain")
    async def test_expire_at_metadata_set(
        self,
        mock_load_urls,
        mock_get_collection,
        mock_get_embeddings,
    ):
        """Test that expire_at is set in chunk metadata."""
        from backend.ingestion.temp_knowledge import ingest_urls_to_temp

        mock_load_urls.return_value = [{
            "content": "Test content for expiration test. " * 5,
            "source": "https://example.com",
            "title": "Test",
        }]

        mock_embeddings = MagicMock()
        mock_embeddings.embed_documents.return_value = [[0.1] * 768]
        mock_get_embeddings.return_value = mock_embeddings

        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        await ingest_urls_to_temp(
            session_id="test-session",
            urls=["https://example.com"],
            expire_hours=24,
        )

        # Verify add was called with metadatas containing expire_at
        call_args = mock_collection.add.call_args
        metadatas = call_args.kwargs.get("metadatas", [])

        assert len(metadatas) > 0
        for meta in metadatas:
            assert "expire_at" in meta
            assert "created_at" in meta
            assert "source_type" in meta
            assert meta["source_type"] == "url"

    def test_cleanup_expired_documents(self):
        """Test cleanup of expired documents."""
        from backend.ingestion.temp_knowledge import cleanup_expired_documents

        with patch(
            "backend.ingestion.temp_knowledge.get_temp_collection"
        ) as mock_get_coll:
            mock_collection = MagicMock()

            # Create expired metadata
            expired_time = (datetime.now() - timedelta(hours=48)).isoformat()
            valid_time = (datetime.now() + timedelta(hours=24)).isoformat()

            mock_collection.get.return_value = {
                "ids": ["doc1", "doc2", "doc3"],
                "metadatas": [
                    {"expire_at": expired_time},  # Expired
                    {"expire_at": valid_time},    # Valid
                    {},                            # No expire_at
                ]
            }
            mock_get_coll.return_value = mock_collection

            deleted = cleanup_expired_documents("test-session")

            assert deleted == 1
            mock_collection.delete.assert_called_once()


class TestBeautifulSoupTransformer:
    """Tests for HTML cleaning behavior."""

    def test_unwanted_tags_constant(self):
        """Verify UNWANTED_TAGS constant is properly defined."""
        from backend.ingestion.temp_knowledge import UNWANTED_TAGS

        expected_tags = [
            "nav", "footer", "header", "aside",
            "script", "style", "noscript"
        ]

        for tag in expected_tags:
            assert tag in UNWANTED_TAGS

    @pytest.mark.asyncio
    @patch("backend.ingestion.temp_knowledge.AsyncHtmlLoader")
    @patch("backend.ingestion.temp_knowledge.BeautifulSoupTransformer")
    async def test_transformer_called_with_correct_args(
        self,
        mock_bs_class,
        mock_loader_class,
    ):
        """Test that BeautifulSoupTransformer is called correctly."""
        from backend.ingestion.temp_knowledge import (
            UNWANTED_TAGS,
            load_urls_with_langchain,
        )

        mock_doc = Document(
            page_content="<html><body>Content</body></html>",
            metadata={"source": "https://example.com"}
        )

        mock_loader = MagicMock()
        mock_loader.aload = AsyncMock(return_value=[mock_doc])
        mock_loader_class.return_value = mock_loader

        mock_transformer = MagicMock()
        transformed_doc = Document(
            page_content="Extracted content here for testing",
            metadata={"source": "https://example.com"}
        )
        mock_transformer.transform_documents.return_value = [transformed_doc]
        mock_bs_class.return_value = mock_transformer

        await load_urls_with_langchain(["https://example.com"])

        # Verify transform_documents was called with correct args
        mock_transformer.transform_documents.assert_called_once()
        call_kwargs = mock_transformer.transform_documents.call_args.kwargs

        assert call_kwargs.get("tags_to_extract") == ["body"]
        assert call_kwargs.get("unwanted_tags") == UNWANTED_TAGS
        assert call_kwargs.get("remove_comments") is True
