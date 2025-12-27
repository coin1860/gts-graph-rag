"""LangGraph workflow definition with parallel retrieval architecture.

This workflow implements:
- URL intent detection for direct summarization vs RAG query
- Parallel vector + graph + temp retrieval for reduced latency
- URL detection and processing for temp knowledge
- Unified reranking of multi-source results
- Short-circuit logic for file-specific queries
"""


from langgraph.graph import END, START, StateGraph

from backend.agent.nodes import (
    generator,
    grader,
    graph_retriever,
    insufficient_handler,
    reranker,
    retrieval_evaluator,
    router,
    vector_retriever,
)
from backend.agent.state import AgentState
from backend.agent.temp_nodes import temp_retriever, url_processor
from backend.agent.url_intent import direct_url_summarizer, url_intent_detector

# =============================================================================
# Routing Functions
# =============================================================================


def route_after_intent(state: AgentState) -> str:
    """Route based on URL intent detection result.

    If url_summarize_direct is True, go straight to direct_url_summarizer.
    Otherwise, continue to router for normal RAG flow.
    """
    if state.get("url_summarize_direct", False):
        return "direct_url_summarizer"
    return "router"


def route_after_router(state: AgentState) -> list[str]:
    """Route to retrievers based on retrieval_mode and temp data.

    Returns a list of nodes to execute (enables parallel execution).
    - Always includes vector_retriever
    - Add graph_retriever if mode is "parallel"
    - Add url_processor if URLs detected
    - Add temp_retriever if session has temp data
    """
    from backend.ingestion.temp_knowledge import has_temp_data

    mode = state.get("retrieval_mode", "vector_only")
    detected_urls = state.get("detected_urls", [])
    session_id = state.get("session_id")
    temp_files = state.get("temp_files", [])

    nodes = []

    # URL processing first if URLs detected (for RAG flow)
    if detected_urls and session_id:
        nodes.append("url_processor")

    # Standard retrievers - Vector only initially (Sequential flow)
    # Graph will be triggered by retrieval_evaluator if needed
    nodes.append("vector_retriever")

    # Temp retriever if session has temp data (from files or URLs)
    if session_id and (temp_files or detected_urls or has_temp_data(session_id)):
        nodes.append("temp_retriever")

    return nodes if nodes else ["vector_retriever"]


def route_grader(state: AgentState) -> str:
    """Route based on grading result."""
    grade = state.get("grade", "insufficient")
    if grade == "relevant":
        return "generator"
    return "insufficient_handler"


def route_retrieval_evaluator(state: AgentState) -> str:
    """Route based on retrieval evaluation."""
    status = state.get("retrieval_status", "insufficient")
    if status == "sufficient":
        return "reranker"
    return "graph_retriever"


# =============================================================================
# Graph Construction
# =============================================================================

def create_agent_graph() -> StateGraph:
    """Create and compile the LangGraph agent workflow.

    Graph Structure (with URL Intent Detection):

        START
          │
          ▼
    url_intent_detector
          │
          ├───────────────────────┐
          ▼                       ▼
        router            direct_url_summarizer
          │                       │
          ├──────────────┬────────┴───────┐
          ▼              ▼                │
    url_processor  vector_retriever       │
          │              │                │
          │        graph_retriever        │
          │              │                │
          │        temp_retriever         │
          │              │                │
          └──────────────┴────────────────┘
                         │                │
                         ▼                │
                     reranker             │
                         │                │
                         ▼                │
                      grader              │
                         │                │
              ┌──────────┴──────────┐     │
              ▼                     ▼     │
          generator          insufficient│
              │                     │     │
              └──────────┬──────────┘     │
                         │                │
                         └────────────────┘
                                   │
                                   ▼
                                  END
    """
    # Create graph with state
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("url_intent_detector", url_intent_detector)
    graph.add_node("direct_url_summarizer", direct_url_summarizer)
    graph.add_node("router", router)
    graph.add_node("url_processor", url_processor)
    graph.add_node("vector_retriever", vector_retriever)
    graph.add_node("graph_retriever", graph_retriever)
    graph.add_node("temp_retriever", temp_retriever)
    graph.add_node("reranker", reranker)
    graph.add_node("retrieval_evaluator", retrieval_evaluator)
    graph.add_node("grader", grader)
    graph.add_node("generator", generator)
    graph.add_node("insufficient_handler", insufficient_handler)

    # Entry point - first detect URL intent
    graph.add_edge(START, "url_intent_detector")

    # URL intent detector routes to either direct summarizer or normal router
    graph.add_conditional_edges(
        "url_intent_detector",
        route_after_intent,
        {
            "direct_url_summarizer": "direct_url_summarizer",
            "router": "router",
        }
    )

    # Direct URL summarizer goes straight to END
    graph.add_edge("direct_url_summarizer", END)

    # Router -> Retrievers (conditional, potentially parallel)
    graph.add_conditional_edges(
        "router",
        route_after_router,
        ["url_processor", "vector_retriever", "graph_retriever", "temp_retriever"]
    )

    # Vector and Temp feed into Evaluator first
    graph.add_edge("url_processor", "retrieval_evaluator")
    graph.add_edge("vector_retriever", "retrieval_evaluator")
    graph.add_edge("temp_retriever", "retrieval_evaluator")

    # Evaluator determines if Graph is needed
    graph.add_conditional_edges(
        "retrieval_evaluator",
        route_retrieval_evaluator,
        {
            "reranker": "reranker",
            "graph_retriever": "graph_retriever",
        }
    )

    # Graph retriever always goes to reranker (to merge with vector)
    graph.add_edge("graph_retriever", "reranker")

    # Reranker -> Grader
    graph.add_edge("reranker", "grader")

    # Grader -> Generator or Insufficient
    graph.add_conditional_edges(
        "grader",
        route_grader,
        {
            "generator": "generator",
            "insufficient_handler": "insufficient_handler",
        }
    )

    # End nodes
    graph.add_edge("generator", END)
    graph.add_edge("insufficient_handler", END)

    return graph.compile()


# Singleton compiled graph
_agent_graph: StateGraph | None = None


def get_agent_graph() -> StateGraph:
    """Get or create the compiled agent graph."""
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = create_agent_graph()
    return _agent_graph
