"""Agent state definition for LangGraph workflow."""

import operator
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State for the RAG agent workflow.

    Attributes:
        messages: Conversation history (accumulated via add_messages)
        question: Current user question
        org_ids: Organization IDs to search within
        file_ids: Optional specific file IDs to filter
        context: Final merged context for generator (auto-appended)
        vector_context: Context from vector retrieval (auto-appended)
        graph_context: Context from graph retrieval (auto-appended)
        temp_context: Context from temp session retrieval (auto-appended)
        graph_viz_data: Graph visualization data (nodes/edges) for frontend
        steps: Reasoning steps for UI display (auto-appended)
        retrieval_mode: How to retrieve ("vector_only", "parallel")
        grade: Context relevance grade ("relevant", "insufficient")
        answer: Final generated answer
        custom_prompt: Optional custom system prompt from frontend
        session_id: Frontend-generated UUID for temp knowledge isolation
        detected_urls: URLs found in user question
        temp_files: IDs of uploaded temp files for this session

    """

    messages: Annotated[list, add_messages]
    question: str
    org_ids: list[int]
    file_ids: list[int] | None
    context: Annotated[list[dict], operator.add]
    vector_context: Annotated[list[dict], operator.add]
    graph_context: Annotated[list[dict], operator.add]
    temp_context: Annotated[list[dict], operator.add]  # NEW: temp retrieval
    graph_viz_data: dict | None
    steps: Annotated[list[str], operator.add]
    retrieval_mode: str
    grade: str
    answer: str
    custom_prompt: str | None
    session_id: str | None  # NEW: session isolation
    detected_urls: list[str]  # NEW: URLs in question
    temp_files: list[str] | None  # NEW: uploaded temp file IDs
    url_summarize_direct: bool  # NEW: bypass RAG for direct URL summarization

