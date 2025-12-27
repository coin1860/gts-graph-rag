"""LangGraph nodes for temporary knowledge processing.

Nodes:
- url_processor: Detect and ingest URLs from user question
- temp_retriever: Retrieve from session's temp collection

Uses LangChain's AsyncHtmlLoader and BeautifulSoupTransformer
for URL content extraction.
"""

import asyncio

from backend.agent.state import AgentState
from backend.ingestion.temp_knowledge import (
    get_temp_collection,
    has_temp_data,
    ingest_urls_to_temp,
)
from backend.models.embeddings import get_embeddings


def url_processor(state: AgentState) -> dict:
    """Process URLs found in user question using LangChain loaders.

    1. Get detected_urls from router
    2. Use AsyncHtmlLoader + BeautifulSoupTransformer to fetch & clean
    3. Embed to temp ChromaDB collection with expire_at
    4. Update steps for UI feedback
    """
    detected_urls = state.get("detected_urls", [])
    session_id = state.get("session_id")

    steps = []

    if not detected_urls:
        return {"steps": ["📎 No URLs detected in message"]}

    if not session_id:
        return {"steps": ["⚠️ No session_id - skipping URL processing"]}

    steps.append(f"🔗 Found {len(detected_urls)} URL(s) in message")

    # Limit to 5 URLs max
    urls_to_process = detected_urls[:5]

    # Process URLs using LangChain async loader
    try:
        steps.append("📥 Fetching URL content with AsyncHtmlLoader...")

        # Run async in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            chunk_ids, total_chars = loop.run_until_complete(
                ingest_urls_to_temp(session_id, urls_to_process)
            )
        finally:
            loop.close()

        if chunk_ids:
            steps.append(f"✅ Extracted {total_chars} chars → {len(chunk_ids)} chunks")
            steps.append("🧹 Cleaned HTML (removed nav/footer/script)")
        else:
            steps.append("⚠️ No content extracted from URLs")

    except Exception as e:
        steps.append(f"❌ URL processing failed: {str(e)[:50]}")

    return {"steps": steps}


def temp_retriever(state: AgentState) -> dict:
    """Retrieve from session's temporary collection.

    Similar to vector_retriever but uses temp collection.
    """
    question = state["question"]
    session_id = state.get("session_id")

    steps = ["🗂️ Searching temporary knowledge..."]

    if not session_id:
        steps.append("⚠️ No session_id - skipping temp retrieval")
        return {"temp_context": [], "steps": steps}

    if not has_temp_data(session_id):
        steps.append("📭 No temporary data for this session")
        return {"temp_context": [], "steps": steps}

    try:
        # Get embeddings for query
        embeddings = get_embeddings()
        query_vector = embeddings.embed_query(question)

        # Query temp collection
        collection = get_temp_collection(session_id)
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=5,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        temp_context = []
        if results and results["ids"] and results["ids"][0]:
            for i, _doc_id in enumerate(results["ids"][0]):
                doc = results["documents"][0][i] if results["documents"] else ""
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                dist = results["distances"][0][i] if results["distances"] else 1.0

                # Convert distance to similarity score
                score = max(0, 1 - dist)

                temp_context.append({
                    "content": doc,
                    "source": meta.get("source", "temp"),
                    "source_type": meta.get("source_type", "temp"),
                    "score": score,
                    "metadata": meta,
                })

        steps.append(f"📎 Retrieved {len(temp_context)} items from temp storage")

        if temp_context:
            for i, ctx in enumerate(temp_context[:3]):
                source = ctx.get("source", "unknown")[:30]
                steps.append(f"  [{i+1}] {source} (score: {ctx['score']:.2f})")

        return {"temp_context": temp_context, "steps": steps}

    except Exception as e:
        steps.append(f"❌ Temp retrieval error: {str(e)[:50]}")
        return {"temp_context": [], "steps": steps}
