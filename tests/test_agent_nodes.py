"""Unit tests for agent nodes.

Tests cover:
- Router node routing logic
- Vector retriever with mocked ChromaDB
- Graph retriever with mocked Neo4j
- Grader with mocked LLM
- Generator with mocked LLM
"""

import pytest
from unittest.mock import MagicMock, patch


class TestRouter:
    """Tests for router node."""

    def test_vector_only_with_selected_files(self, sample_agent_state):
        """Router should return vector_only when files are selected."""
        from backend.agent.nodes import router

        state = sample_agent_state.copy()
        state["file_ids"] = [1, 2, 3]

        result = router(state)

        assert result["retrieval_mode"] == "vector_only"
        assert "steps" in result
        assert len(result["steps"]) > 0

    def test_parallel_without_selected_files(self, sample_agent_state):
        """Router should return parallel when no files selected."""
        from backend.agent.nodes import router

        state = sample_agent_state.copy()
        state["file_ids"] = []

        result = router(state)

        assert result["retrieval_mode"] == "parallel"

    @pytest.mark.parametrize("files,expected_mode", [
        ([], "parallel"),
        ([1], "vector_only"),
        ([1, 2, 3], "vector_only"),
        (None, "parallel"),
    ])
    def test_routing_parametrized(self, sample_agent_state, files, expected_mode):
        """Parametrized test for routing logic."""
        from backend.agent.nodes import router

        state = sample_agent_state.copy()
        state["file_ids"] = files or []

        result = router(state)

        assert result["retrieval_mode"] == expected_mode



class TestVectorRetriever:
    """Tests for vector retriever node."""

    @patch("backend.agent.nodes.get_chroma_collection")
    @patch("backend.agent.nodes.get_embeddings")
    def test_retrieval_success(
        self,
        mock_get_embeddings,
        mock_get_collection,
        sample_agent_state,
        mock_embeddings,
        mock_chroma_collection,
    ):
        """Test successful vector retrieval."""
        mock_get_embeddings.return_value = mock_embeddings
        mock_get_collection.return_value = mock_chroma_collection
        
        from backend.agent.nodes import vector_retriever
        
        result = vector_retriever(sample_agent_state)
        
        assert "vector_context" in result
        assert "steps" in result

    @patch("backend.agent.nodes.get_chroma_collection")
    @patch("backend.agent.nodes.get_embeddings")
    def test_empty_results(
        self,
        mock_get_embeddings,
        mock_get_collection,
        sample_agent_state,
        mock_embeddings,
    ):
        """Test handling of empty results."""
        mock_get_embeddings.return_value = mock_embeddings
        
        empty_collection = MagicMock()
        empty_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        mock_get_collection.return_value = empty_collection
        
        from backend.agent.nodes import vector_retriever
        
        result = vector_retriever(sample_agent_state)
        
        assert result.get("vector_context", []) == []

    @pytest.mark.parametrize("query", [
        "What is BOI?",
        "How does the system work?",
        "Tell me about microservices",
        "",  # Edge case: empty query
    ])
    @patch("backend.agent.nodes.get_chroma_collection")
    @patch("backend.agent.nodes.get_embeddings")
    def test_various_queries(
        self,
        mock_get_embeddings,
        mock_get_collection,
        sample_agent_state,
        mock_embeddings,
        mock_chroma_collection,
        query,
    ):
        """Test with various query types."""
        mock_get_embeddings.return_value = mock_embeddings
        mock_get_collection.return_value = mock_chroma_collection
        
        from backend.agent.nodes import vector_retriever
        
        state = sample_agent_state.copy()
        state["question"] = query
        
        result = vector_retriever(state)
        
        assert "steps" in result


class TestGraphRetriever:
    """Tests for graph retriever node."""

    @patch("backend.agent.nodes.get_cypher_chain")
    @patch("backend.agent.nodes.get_neo4j_graph")
    def test_successful_graph_query(
        self,
        mock_get_graph,
        mock_get_chain,
        sample_agent_state,
        mock_neo4j_graph,
        mock_cypher_chain,
    ):
        """Test successful graph retrieval."""
        mock_get_graph.return_value = mock_neo4j_graph
        mock_get_chain.return_value = mock_cypher_chain
        
        from backend.agent.nodes import graph_retriever
        
        result = graph_retriever(sample_agent_state)
        
        assert "graph_context" in result or "steps" in result

    @patch("backend.agent.nodes.get_cypher_chain")
    def test_no_neo4j_connection(
        self,
        mock_get_chain,
        sample_agent_state,
    ):
        """Test handling when Neo4j is not available."""
        mock_get_chain.return_value = None
        
        from backend.agent.nodes import graph_retriever
        
        result = graph_retriever(sample_agent_state)
        
        assert "steps" in result
        # Should contain warning about unavailable connection
        assert any("not available" in str(step).lower() or "failed" in str(step).lower() 
                   for step in result.get("steps", []))

    @patch("backend.agent.nodes.get_cypher_chain")
    @patch("backend.agent.nodes.get_neo4j_graph")
    def test_cypher_error_handling(
        self,
        mock_get_graph,
        mock_get_chain,
        sample_agent_state,
        mock_neo4j_graph,
    ):
        """Test handling of Cypher execution errors."""
        mock_get_graph.return_value = mock_neo4j_graph
        
        error_chain = MagicMock()
        error_chain.invoke.side_effect = Exception("SyntaxError in Cypher")
        mock_get_chain.return_value = error_chain
        
        from backend.agent.nodes import graph_retriever
        
        result = graph_retriever(sample_agent_state)
        
        # Should handle error gracefully
        assert "steps" in result


class TestGrader:
    """Tests for grader node."""

    @patch("backend.agent.nodes.get_llm")
    def test_relevant_context(
        self,
        mock_get_llm,
        sample_agent_state,
        sample_context,
    ):
        """Test grading context as relevant."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="YES")
        mock_get_llm.return_value = mock_llm

        from backend.agent.nodes import grader

        state = sample_agent_state.copy()
        state["context"] = sample_context

        result = grader(state)

        assert result.get("grade") == "relevant"

    @patch("backend.agent.nodes.get_llm")
    def test_insufficient_context(
        self,
        mock_get_llm,
        sample_agent_state,
    ):
        """Test grading context as insufficient when NO returned."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="NO")
        mock_get_llm.return_value = mock_llm

        from backend.agent.nodes import grader

        state = sample_agent_state.copy()
        state["context"] = [{"content": "test", "source": "test.pdf", "score": 0.5}]

        result = grader(state)

        assert result.get("grade") == "insufficient"

    def test_empty_context(self, sample_agent_state):
        """Test handling of empty context."""
        from backend.agent.nodes import grader

        state = sample_agent_state.copy()
        state["context"] = []

        result = grader(state)

        # Empty context should be marked as insufficient
        assert result.get("grade") == "insufficient"


class TestGenerator:
    """Tests for generator node."""

    @patch("backend.agent.nodes.get_llm")
    def test_successful_generation(
        self,
        mock_get_llm,
        sample_agent_state,
        sample_context,
    ):
        """Test successful answer generation."""
        from backend.agent.nodes import generator

        state = sample_agent_state.copy()
        state["context"] = sample_context

        result = generator(state)

        # Generator should return steps and answer
        assert "steps" in result

    @patch("backend.agent.nodes.get_llm")
    def test_generation_with_empty_context(
        self,
        mock_get_llm,
        sample_agent_state,
    ):
        """Test generation with empty context."""
        mock_llm = MagicMock()
        mock_llm.stream.return_value = iter([
            MagicMock(content="I don't have enough information."),
        ])
        mock_get_llm.return_value = mock_llm
        
        from backend.agent.nodes import generator
        
        state = sample_agent_state.copy()
        state["context"] = []
        
        result = generator(state)
        
        assert "answer" in result


class TestInsufficientHandler:
    """Tests for insufficient handler node."""

    def test_returns_fallback_message(self, sample_agent_state):
        """Test that handler returns appropriate fallback."""
        from backend.agent.nodes import insufficient_handler
        
        result = insufficient_handler(sample_agent_state)
        
        assert "answer" in result
        assert len(result["answer"]) > 0
