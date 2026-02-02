"""Embedding model wrapper for vector embeddings.
Supports OpenAI-compatible API endpoints.
"""


from openai import OpenAI

from backend.config import settings


class DashScopeEmbeddings:
    """Embeddings wrapper using OpenAI-compatible interface.
    Compatible with neo4j-graphrag Embedder interface.
    """

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        **kwargs
    ):
        self.model = model or settings.embedding_model

        # Use OpenAI-compatible client
        self.client = OpenAI(
            api_key=api_key or settings.embedding_api_key,
            base_url=base_url or settings.embedding_base_url,
        )

    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single text query.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        """
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )

        return response.data[0].embedding

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple documents.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        """
        # Process in batches of 25 (API limit for some providers)
        embeddings = []
        batch_size = 25

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
            )

            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)

        return embeddings

    async def aembed_query(self, text: str) -> list[float]:
        """Async version of embed_query."""
        # Use sync version for now
        return self.embed_query(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Async version of embed_documents."""
        return self.embed_documents(texts)


# Singleton instance
_embeddings_instance: DashScopeEmbeddings | None = None


def get_embeddings() -> DashScopeEmbeddings:
    """Get or create the embeddings instance."""
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = DashScopeEmbeddings()
    return _embeddings_instance

