"""Chat routes - Streaming chat with LangGraph agent.
Uses LangGraph astream_events v2 for real-time LLM token streaming.
"""

import json
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.agent.graph import get_agent_graph
from backend.auth.dependencies import get_current_active_user
from backend.config import settings
from backend.database import get_db
from backend.models.db_models import User, UserRole

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    """Chat request body."""

    message: str
    org_ids: list[int] | None = None
    file_ids: list[int] | None = None
    custom_prompt: str | None = None
    session_id: str | None = None  # For temp knowledge isolation
    temp_file_ids: list[str] | None = None  # Uploaded temp file IDs


class ChatMessage(BaseModel):
    """Chat message for history."""

    role: str
    content: str


# Node display names for UI
NODE_DISPLAY_NAMES = {
    "url_intent_detector": "🔍 Intent Detector",
    "direct_url_summarizer": "📄 URL Summarizer",
    "router": "🔀 Router",
    "url_processor": "🔗 URL Processor",
    "vector_retriever": "🔍 Vector Search",
    "graph_retriever": "📊 Graph Search",
    "temp_retriever": "📎 Temp Knowledge",
    "reranker": "🔄 Reranker",
    "grader": "✅ Quality Check",
    "generator": "💡 Generator",
    "insufficient_handler": "⚠️ Fallback",
}


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Stream chat using LangGraph astream_events v2 protocol.

    Streams real-time events:
    - node_start: When a node begins execution
    - node_end: When a node completes
    - llm_token: Real-time LLM token streaming (on_chat_model_stream)
    - data_sources: Retrieved sources
    """
    message_id = str(uuid4())

    # Determine accessible org_ids
    if current_user.role == UserRole.ADMIN:
        org_ids = request.org_ids
    else:
        user_org_ids = [org.id for org in current_user.organizations]
        if request.org_ids:
            org_ids = [oid for oid in request.org_ids if oid in user_org_ids]
        else:
            org_ids = user_org_ids

    if not org_ids:
        org_ids = []

    async def generate():
        """Generate SSE stream with LangGraph astream_events v2."""
        yield f"data: {json.dumps({'type': 'start', 'messageId': message_id})}\n\n"

        try:
            graph = get_agent_graph()

            # Initial state
            initial_state = {
                "messages": [],
                "question": request.message,
                "org_ids": org_ids,
                "file_ids": request.file_ids,
                "context": [],
                "vector_context": [],
                "graph_context": [],
                "temp_context": [],  # Temp retrieval results
                "graph_viz_data": None,
                "steps": [],
                "retrieval_mode": "",
                "grade": "",
                "answer": "",
                "custom_prompt": request.custom_prompt,
                "session_id": request.session_id,  # Session isolation
                "detected_urls": [],  # Populated by router
                "temp_files": request.temp_file_ids,  # Uploaded temp files
                "url_summarize_direct": False,  # NEW: set by url_intent_detector
            }

            # Track state
            active_nodes = set()
            final_answer = ""
            final_sources = []

            # Use astream_events v2 for token-level streaming
            async for event in graph.astream_events(initial_state, version="v2"):
                kind = event.get("event", "")
                metadata = event.get("metadata", {})
                node_name = metadata.get("langgraph_node", "")

                display_name = NODE_DISPLAY_NAMES.get(node_name, node_name)

                # ============================================================
                # Node Start - Show "Processing..." status
                # ============================================================
                if kind == "on_chain_start" and node_name and node_name not in active_nodes:
                    active_nodes.add(node_name)
                    yield f"data: {json.dumps({'type': 'node-start', 'data': {'node': node_name, 'display': display_name}})}\n\n"

                # ============================================================
                # LLM Token Streaming (REAL-TIME)
                # This is the key event for showing LLM thinking
                # ============================================================
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk", None)
                    if chunk:
                        content = ""
                        if hasattr(chunk, "content"):
                            content = chunk.content
                        elif isinstance(chunk, dict):
                            content = chunk.get("content", "")

                        if content:
                            # Stream token with node context
                            yield f"data: {json.dumps({'type': 'llm-token', 'data': {'token': content, 'node': node_name}})}\n\n"

                            # If this is the generator, accumulate for final answer
                            if node_name == "generator":
                                final_answer += content

                # ============================================================
                # Node End - Extract results and mark complete
                # ============================================================
                elif kind == "on_chain_end" and node_name:
                    output = event.get("data", {}).get("output", {})

                    if isinstance(output, dict):
                        # Extract steps (static messages)
                        steps = output.get("steps", [])
                        if steps:
                            yield f"data: {json.dumps({'type': 'node-steps', 'data': {'node': node_name, 'steps': steps}})}\n\n"

                        # Extract graph visualization data from graph_retriever
                        if node_name == "graph_retriever":
                            print(f"🔍 graph_retriever output keys: {output.keys() if isinstance(output, dict) else type(output)}")
                            if "graph_viz_data" in output:
                                graph_viz_data = output["graph_viz_data"]
                                nodes = graph_viz_data.get("nodes", [])
                                links = graph_viz_data.get("links", [])
                                print(f"📊 Sending graph-data: {len(nodes)} nodes, {len(links)} links")

                                if nodes:
                                    yield f"data: {json.dumps({'type': 'graph-data', 'data': {'nodes': nodes, 'links': links}})}\n\n"
                            else:
                                print("⚠️ No graph_viz_data in graph_retriever output")


                        # Extract sources from reranker
                        if node_name == "reranker" and "context" in output:
                            context = output["context"]
                            min_score = settings.min_relevance_score
                            final_sources = [
                                {
                                    "content": c.get("content", ""),
                                    "source": c.get("metadata", {}).get("source", c.get("retrieval_source", "Unknown")),
                                    "score": round(c.get("score", 0), 3),
                                    "metadata": c.get("metadata", {}),
                                }
                                for c in context if c.get("score", 0) >= min_score
                            ][:5]
                            yield f"data: {json.dumps({'type': 'data-sources', 'data': {'sources': final_sources}})}\n\n"

                        # Capture final answer (if not streamed)
                        if node_name == "generator" and "answer" in output and not final_answer:
                            final_answer = output["answer"]

                        # Capture answer from direct_url_summarizer (bypasses generator)
                        if node_name == "direct_url_summarizer" and "answer" in output and not final_answer:
                            final_answer = output["answer"]
                            # Also extract sources if present
                            if "context" in output:
                                context = output["context"]
                                final_sources = [
                                    {
                                        "content": c.get("content", ""),
                                        "source": c.get("source", "URL"),
                                        "score": 1.0,
                                        "metadata": {},
                                    }
                                    for c in context
                                ]
                                yield f"data: {json.dumps({'type': 'data-sources', 'data': {'sources': final_sources}})}\n\n"

                    # Mark node complete
                    yield f"data: {json.dumps({'type': 'node-end', 'data': {'node': node_name, 'display': display_name}})}\n\n"

            # Stream final answer if not already streamed via tokens
            if final_answer:
                yield f"data: {json.dumps({'type': 'text-start', 'id': message_id})}\n\n"
                # Check if we already streamed tokens (from generator)
                # If not, stream character by character
                yield f"data: {json.dumps({'type': 'text-content', 'id': message_id, 'content': final_answer})}\n\n"
                yield f"data: {json.dumps({'type': 'text-end', 'id': message_id})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'text-content', 'id': message_id, 'content': 'No answer could be generated.'})}\n\n"

            yield f"data: {json.dumps({'type': 'finish', 'finishReason': 'stop'})}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': f'Agent error: {str(e)[:100]}'})}\n\n"
            yield f"data: {json.dumps({'type': 'finish', 'finishReason': 'error'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
