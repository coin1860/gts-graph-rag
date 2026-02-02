"""RAG service module - Core RAG functionality shared by API and MCP.

This module provides the core RAG query functionality that can be used by:
1. REST API (/api/chat)
2. MCP tools (rag_chat, search_knowledge)
"""

from backend.config import settings
from backend.agent.graph import get_agent_graph
from backend.models.embeddings import get_embeddings
from backend.ingestion.ingest import get_chroma_collection


async def run_rag_query(
    question: str,
    org_ids: list[int],
    file_ids: list[int] | None = None,
    custom_prompt: str | None = None,
    session_id: str | None = None,
    temp_file_ids: list[str] | None = None,
) -> str:
    """Run a RAG query and return the final answer.
    
    This is the core RAG function used by both REST API and MCP tools.
    
    Args:
        question: The user's question
        org_ids: Organization IDs to search within
        file_ids: Optional specific file IDs to search
        custom_prompt: Optional custom prompt
        session_id: Optional session ID for temp knowledge isolation
        temp_file_ids: Optional uploaded temp file IDs
        
    Returns:
        The generated answer string
    """
    graph = get_agent_graph()
    
    # Initial state for LangGraph
    initial_state = {
        "messages": [],
        "question": question,
        "org_ids": org_ids,
        "file_ids": file_ids,
        "context": [],
        "vector_context": [],
        "graph_context": [],
        "temp_context": [],
        "graph_viz_data": None,
        "steps": [],
        "retrieval_mode": "",
        "grade": "",
        "answer": "",
        "custom_prompt": custom_prompt,
        "session_id": session_id,
        "detected_urls": [],
        "temp_files": temp_file_ids,
        "url_summarize_direct": False,
    }
    
    # Run the graph and collect the final answer
    final_answer = ""
    
    async for event in graph.astream_events(initial_state, version="v2"):
        kind = event.get("event", "")
        metadata = event.get("metadata", {})
        node_name = metadata.get("langgraph_node", "")
        
        # Collect tokens from generator
        if kind == "on_chat_model_stream" and node_name == "generator":
            chunk = event.get("data", {}).get("chunk", None)
            if chunk:
                content = ""
                if hasattr(chunk, "content"):
                    content = chunk.content
                elif isinstance(chunk, dict):
                    content = chunk.get("content", "")
                if content:
                    final_answer += content
        
        # Capture answer from output if not streamed
        elif kind == "on_chain_end" and node_name in ("generator", "direct_url_summarizer"):
            output = event.get("data", {}).get("output", {})
            if isinstance(output, dict) and "answer" in output and not final_answer:
                final_answer = output["answer"]
    
    return final_answer if final_answer else ""


def search_vector_store(
    question: str,
    org_ids: list[int],
    top_k: int = 3,
) -> list[dict]:
    """Search the vector store for relevant knowledge snippets.
    
    Args:
        question: The search query
        org_ids: Organization IDs to search within
        top_k: Number of results to return
        
    Returns:
        List of dicts with 'content', 'source', 'score' keys
    """
    # Get embeddings and collection
    embeddings = get_embeddings()
    collection = get_chroma_collection()
    
    # Embed the question
    query_embedding = embeddings.embed_query(question)
    
    # Build filter for organization
    where_filter = {"org_id": {"$in": org_ids}} if org_ids else None
    
    # Query ChromaDB
    query_kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_filter:
        query_kwargs["where"] = where_filter
    
    results = collection.query(**query_kwargs)
    
    # Check if we got results
    if not results or not results.get("documents") or not results["documents"][0]:
        return []
    
    # Format results
    documents = results["documents"][0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    
    snippets = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        # Convert distance to similarity score (ChromaDB uses L2 distance)
        score = round(1 / (1 + dist), 3) if dist >= 0 else 0.5
        source = meta.get("source", "Unknown") if meta else "Unknown"
        
        snippets.append({
            "content": doc,
            "source": source,
            "score": score,
            "metadata": meta or {},
        })
    
    return snippets


def format_knowledge_for_llm(
    question: str,
    snippets: list[dict],
) -> str:
    """Format knowledge snippets into a prompt for external LLM.
    
    Args:
        question: The user's question
        snippets: List of knowledge snippet dicts
        
    Returns:
        Formatted prompt string
    """
    if not snippets:
        return f"在知识库中没有找到与问题相关的内容。\n\n问题: {question}"
    
    output_lines = [
        "你是一个知识助手。请根据以下知识片段回答用户的问题。",
        "",
        "## 用户问题",
        question,
        "",
        "## 相关知识片段",
        "",
    ]
    
    for i, snippet in enumerate(snippets, 1):
        output_lines.extend([
            f"### 片段 {i} (相关度: {snippet['score']}, 来源: {snippet['source']})",
            snippet["content"],
            "",
        ])
    
    output_lines.extend([
        "---",
        "",
        "请根据以上知识片段，为用户提供准确、全面的回答。如果知识片段中没有相关信息，请明确说明。",
    ])
    
    return "\n".join(output_lines)
