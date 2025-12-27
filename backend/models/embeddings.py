"""DashScope text-embedding-v1 wrapper for vector embeddings."""


import dashscope
from dashscope import TextEmbedding

from backend.config import settings


class DashScopeEmbeddings:
    """DashScope embeddings wrapper for text-embedding-v1.
    Compatible with neo4j-graphrag Embedder interface.
    """

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        **kwargs
    ):
        self.model = model or settings.embedding_model

        # Set DashScope API key
        dashscope.api_key = api_key or settings.dashscope_api_key

    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single text query.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        """
        response = TextEmbedding.call(
            model=self.model,
            input=text,
        )

        if response.status_code != 200:
            raise Exception(f"Embedding failed: {response.message}")

        return response.output["embeddings"][0]["embedding"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple documents.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        """
        # DashScope supports batch embedding
        # Process in batches of 25 (API limit)
        embeddings = []
        batch_size = 25

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = TextEmbedding.call(
                model=self.model,
                input=batch,
            )

            if response.status_code != 200:
                raise Exception(f"Embedding failed: {response.message}")

            batch_embeddings = [
                item["embedding"]
                for item in response.output["embeddings"]
            ]
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
