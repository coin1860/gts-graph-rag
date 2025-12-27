"""DashScope Rerank model wrapper for relevance filtering.
Uses the gte-rerank model via DashScope API.
"""


import dashscope
from dashscope import TextReRank

from backend.config import settings


class DashScopeRerank:
    """DashScope rerank wrapper for gte-rerank model.
    Reranks documents based on relevance to query.
    """

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        **kwargs
    ):
        self.model = model or settings.rerank_model

        # Set DashScope API key
        dashscope.api_key = api_key or settings.dashscope_api_key

    def rerank(
        self,
        query: str,
        documents: list[dict],
        top_n: int = None,
        min_score: float = None,
    ) -> list[dict]:
        """Rerank documents based on relevance to query.

        Args:
            query: The search query
            documents: List of documents with 'content' field
            top_n: Maximum number of results to return
            min_score: Minimum relevance score threshold

        Returns:
            Reranked and filtered list of documents with scores

        """
        if not documents:
            return []

        top_n = top_n or settings.vector_search_results
        min_score = min_score or settings.min_relevance_score

        # Extract text content for reranking
        texts = [doc.get("content", "")[:2000] for doc in documents]  # Limit text length

        try:
            response = TextReRank.call(
                model=self.model,
                query=query,
                documents=texts,
                top_n=min(top_n * 2, len(texts)),  # Get more to filter by score
                return_documents=False,
            )

            if response.status_code != 200:
                # Fallback: return original documents sorted by existing score
                return sorted(
                    documents[:top_n],
                    key=lambda x: x.get("score", 0),
                    reverse=True
                )

            # Build reranked results
            reranked = []
            for result in response.output.get("results", []):
                idx = result.get("index", 0)
                score = result.get("relevance_score", 0)

                if score >= min_score and idx < len(documents):
                    doc = documents[idx].copy()
                    doc["score"] = score
                    doc["rerank_score"] = score
                    reranked.append(doc)

            # Sort by score and limit
            reranked.sort(key=lambda x: x.get("score", 0), reverse=True)
            return reranked[:top_n]

        except Exception as e:
            # Fallback on error
            print(f"Rerank error: {e}")
            return sorted(
                documents[:top_n],
                key=lambda x: x.get("score", 0),
                reverse=True
            )


# Singleton instance
_rerank_instance: DashScopeRerank | None = None


def get_rerank() -> DashScopeRerank:
    """Get or create the rerank instance."""
    global _rerank_instance
    if _rerank_instance is None:
        _rerank_instance = DashScopeRerank()
    return _rerank_instance
