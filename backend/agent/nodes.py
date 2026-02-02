"""LangGraph node implementations for the RAG agent.

Refactored to use:
- Global singletons for LLM and Neo4j connections
- LangGraph's automatic state merging (no more steps.copy())
- LangChain native components for better compatibility
"""

from langchain_core.prompts import ChatPromptTemplate

from backend.agent.state import AgentState
from backend.config import settings
from backend.ingestion.ingest import get_chroma_collection
from backend.models.embeddings import get_embeddings
from backend.models.llm import get_langchain_llm, get_llm
from backend.models.rerank import get_rerank, is_rerank_enabled

# =============================================================================
# Global Singletons (initialized lazily, not on every request)
# =============================================================================

_neo4j_graph = None
_cypher_chain = None


def get_neo4j_graph():
    """Get or create Neo4jGraph singleton."""
    global _neo4j_graph
    if _neo4j_graph is None:
        try:
            from langchain_neo4j import Neo4jGraph
            print(f"🔗 Connecting to Neo4j: {settings.neo4j_uri}")
            _neo4j_graph = Neo4jGraph(
                url=settings.neo4j_uri,
                username=settings.neo4j_username,
                password=settings.neo4j_password,
                database=settings.neo4j_database,
            )
            print("✅ Neo4jGraph connected successfully")
        except ImportError as e:
            print(f"⚠️ Neo4j import error: {e}")
            print("   Install with: pip install langchain-community neo4j")
            return None
        except Exception as e:
            print(f"⚠️ Failed to initialize Neo4jGraph: {type(e).__name__}: {e}")
            return None
    return _neo4j_graph


def get_cypher_chain():
    """Get or create GraphCypherQAChain singleton."""
    global _cypher_chain
    if _cypher_chain is None:
        graph = get_neo4j_graph()
        if graph is None:
            return None
        try:
            from langchain_neo4j import GraphCypherQAChain
            _cypher_chain = GraphCypherQAChain.from_llm(
                llm=get_langchain_llm(),
                graph=graph,
                verbose=False,
                return_intermediate_steps=True,
                allow_dangerous_requests=True,  # Required for Cypher execution
            )
            print("✅ GraphCypherQAChain initialized successfully")
        except Exception as e:
            print(f"⚠️ Failed to initialize GraphCypherQAChain: {e}")
            return None
    return _cypher_chain


# =============================================================================
# Node Functions (simplified with auto-merging state)
# =============================================================================

def router(state: AgentState) -> dict:
    """Router node for parallel retrieval architecture.

    Decision logic:
    - Detect URLs in question for temp processing
    - If specific files selected, use vector_only
    - Otherwise, use parallel (vector + graph)
    """
    import re

    question = state.get("question", "")

    # Detect URLs in question
    url_pattern = r"https?://[^\s<>\"')\]]+|www\.[^\s<>\"')\]]+"
    detected_urls = re.findall(url_pattern, question)
    # Clean URLs
    detected_urls = [
        url.rstrip(".,;:!?") for url in detected_urls
    ]
    detected_urls = list(set(detected_urls))

    steps = ["🔀 Analyzing query..."]

    if detected_urls:
        steps.append(f"🔗 Detected {len(detected_urls)} URL(s) in message")

    # Check if specific files are selected - use vector only
    file_ids = state.get("file_ids")
    if file_ids and len(file_ids) > 0:
        steps.append("📁 File filter active - using vector search only")
        return {
            "retrieval_mode": "vector_only",
            "detected_urls": detected_urls,
            "steps": steps,
        }

    # Default to parallel retrieval
    steps.append("🚀 Using parallel retrieval (Vector + Graph)")
    return {
        "retrieval_mode": "parallel",
        "detected_urls": detected_urls,
        "steps": steps,
    }



def vector_retriever(state: AgentState) -> dict:
    """Retrieve context from ChromaDB using vector similarity search."""
    question = state["question"]
    org_ids = state.get("org_ids", [])
    file_ids = state.get("file_ids")

    # Get embeddings singleton
    embedder = get_embeddings()
    query_embedding = embedder.embed_query(question)

    # Query each org's collection
    all_results = []
    collections_to_query = org_ids if org_ids else [None]

    steps = ["🔍 Searching vector database (ChromaDB)..."]

    for org_id in collections_to_query:
        try:
            collection = get_chroma_collection(org_id)

            # Build filter for specific files if requested
            where_filter = None
            if file_ids:
                where_filter = {"doc_id": {"$in": file_ids}}

            results = collection.query(
                query_embeddings=[query_embedding],
                where=where_filter,
                n_results=settings.vector_search_results * 2,  # Get more for reranking
                include=["documents", "metadatas", "distances"],
            )

            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    all_results.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "score": 1 - results["distances"][0][i] if results["distances"] else 0,
                        "source": "vector",
                    })
        except Exception as e:
            steps.append(f"⚠️ Vector search warning: {str(e)[:50]}")

    # Sort by initial score
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Apply reranking if enabled and we have results
    if all_results and is_rerank_enabled():
        steps.append("🔄 Reranking results for relevance...")
        try:
            reranker = get_rerank()
            if reranker:
                reranked_results = reranker.rerank(
                    query=question,
                    documents=all_results,
                    top_n=settings.vector_search_results,
                    min_score=settings.min_relevance_score,
                )
                steps.append(f"✅ Found {len(reranked_results)} relevant chunks after reranking")
                # Output to vector_context (will be merged by reranker node)
                return {
                    "vector_context": reranked_results,
                    "steps": steps,
                }
        except Exception as e:
            steps.append(f"⚠️ Rerank warning: {str(e)[:50]}, using original scores")

    # Fallback: use original scoring (or if rerank is disabled)
    top_results = all_results[:settings.vector_search_results]
    steps.append(f"✅ Found {len(top_results)} relevant chunks from vector search")

    # Output to vector_context (will be merged by reranker)
    return {
        "vector_context": top_results,
        "steps": steps,
    }

def graph_retriever(state: AgentState) -> dict:
    """Retrieve context from Neo4j using GraphCypherQAChain (Text2Cypher).
    Includes proper graph visualization data extraction with real relationships.
    """
    question = state["question"]
    steps = ["📊 Querying Knowledge Graph (Neo4j)..."]

    chain = get_cypher_chain()
    if chain is None:
        steps.append("⚠️ Graph retrieval not available - Neo4j connection failed")
        return {"steps": steps}

    def format_neo4j_to_viz(records: list) -> dict:
        """Convert Neo4j query results (Node, Relationship, Path) to frontend-compatible JSON.
        Uses element_id for proper Neo4j 2025 compatibility.
        """
        nodes = []
        links = []
        node_ids = set()
        link_ids = set()

        def process_node(node_data, label_hint: str = "Entity"):
            """Process a single node (dict from Neo4j)."""
            # Handle dict format from langchain_neo4j
            if isinstance(node_data, dict):
                node_id = node_data.get("id", node_data.get("name", str(hash(str(node_data)))[:8]))
                if node_id and node_id not in node_ids:
                    node_ids.add(node_id)
                    label = node_data.get("name", node_data.get("id", node_data.get("title", str(node_id))))
                    nodes.append({
                        "id": str(node_id),
                        "label": str(label)[:30],
                        "type": label_hint,
                        "properties": node_data
                    })
                    return str(node_id)
            # Handle Neo4j Node objects (with element_id)
            elif hasattr(node_data, 'element_id'):
                eid = node_data.element_id
                if eid not in node_ids:
                    node_ids.add(eid)
                    props = dict(node_data) if hasattr(node_data, 'keys') else {}
                    label = props.get("name", props.get("id", props.get("title", "")))
                    if not label and hasattr(node_data, 'labels'):
                        label = list(node_data.labels)[0] if node_data.labels else "Node"
                    node_type = list(node_data.labels)[0] if hasattr(node_data, 'labels') and node_data.labels else "Entity"
                    nodes.append({
                        "id": eid,
                        "label": str(label)[:30],
                        "type": node_type,
                        "properties": props
                    })
                    return eid
            return None

        def process_relationship(rel_data):
            """Process a relationship."""
            if hasattr(rel_data, 'element_id') and hasattr(rel_data, 'start_node') and hasattr(rel_data, 'end_node'):
                rid = rel_data.element_id
                if rid not in link_ids:
                    link_ids.add(rid)
                    source_id = process_node(rel_data.start_node)
                    target_id = process_node(rel_data.end_node)
                    if source_id and target_id:
                        links.append({
                            "id": rid,
                            "source": source_id,
                            "target": target_id,
                            "label": rel_data.type if hasattr(rel_data, 'type') else "RELATED"
                        })

        # Process each record
        for record in records:
            if isinstance(record, dict):
                # Check if this is a field-based result (e.g. {'u.id': 'xxx', 'u.text': '...'})
                has_field_keys = any('.' in str(k) for k in record.keys())

                if has_field_keys:
                    # Field-based result - create one node per record
                    node_id = None
                    node_label = None

                    for key, value in record.items():
                        if isinstance(value, str) and len(value) < 100:
                            if '.id' in key or 'id' == key.split('.')[-1]:
                                node_id = value
                            elif '.name' in key or '.title' in key:
                                node_label = value

                    if node_id and node_id not in node_ids:
                        node_ids.add(node_id)
                        nodes.append({
                            "id": str(node_id),
                            "label": str(node_label or node_id)[:30],
                            "type": "Document",
                            "properties": record
                        })
                else:
                    # Node/dict-based result
                    for key, value in record.items():
                        # Handle Path objects
                        if hasattr(value, 'nodes') and hasattr(value, 'relationships'):
                            for node in value.nodes:
                                process_node(node)
                            for rel in value.relationships:
                                process_relationship(rel)
                        # Handle single Node
                        elif hasattr(value, 'element_id') or hasattr(value, 'labels'):
                            process_node(value)
                        # Handle relationship
                        elif hasattr(value, 'type') and hasattr(value, 'start_node'):
                            process_relationship(value)
                        # Handle dict (common from langchain_neo4j)
                        elif isinstance(value, dict):
                            process_node(value, key)
                        # Handle lists
                        elif isinstance(value, list):
                            for item in value:
                                if hasattr(item, 'element_id'):
                                    process_node(item)
                                elif isinstance(item, dict):
                                    process_node(item)

        # If we have nodes but no links, create reasonable connections
        if len(nodes) > 1 and len(links) == 0:
            # Connect nodes sequentially (as they appeared in results)
            for i in range(len(nodes) - 1):
                links.append({
                    "source": nodes[i]["id"],
                    "target": nodes[i + 1]["id"],
                    "label": "RELATED"
                })

        return {"nodes": nodes, "links": links}


    try:
        print(f"📊 Graph query for: '{question}'")

        # Use LangChain's Chain to auto-generate and execute Cypher
        result = chain.invoke({"query": question})

        # Extract generated Cypher from intermediate_steps
        cypher_used = ""
        if "intermediate_steps" in result and result["intermediate_steps"]:
            cypher_used = result["intermediate_steps"][0].get("query", "")
            print(f"📊 Generated Cypher: {cypher_used}")

        context_data = result.get("result", "")

        # Extract visualization data by re-executing the Cypher query
        graph_viz_data = {"nodes": [], "links": []}

        try:
            graph = get_neo4j_graph()
            if graph:
                # First try the original Cypher
                if cypher_used:
                    raw_result = graph.query(cypher_used)
                    graph_viz_data = format_neo4j_to_viz(raw_result)

                # If no nodes found, fallback to simple query to show all entities
                if not graph_viz_data["nodes"]:
                    raw_result = graph.query("MATCH (n) RETURN n LIMIT 10")
                    graph_viz_data = format_neo4j_to_viz(raw_result)

                print(f"📊 Graph viz: {len(graph_viz_data['nodes'])} nodes, {len(graph_viz_data['links'])} links")
        except Exception as viz_error:
            print(f"⚠️ Graph visualization extraction failed: {viz_error}")


        if context_data:
            graph_context = [{
                "content": str(context_data),
                "source": "graph",
                "cypher": cypher_used,
                "metadata": {"type": "graph_query"},
                "score": 0.8,
            }]
            steps.append("✅ Found graph data via Text2Cypher")
            return {
                "graph_context": graph_context,
                "graph_viz_data": graph_viz_data,
                "steps": steps,
            }
        else:
            steps.append("ℹ️ No relevant graph data found")
            return {"steps": steps, "graph_viz_data": graph_viz_data}

    except Exception as e:
        error_msg = str(e)
        print(f"⚠️ Graph retriever error: {error_msg}")
        steps.append(f"⚠️ Graph query error: {error_msg[:50]}...")
        return {"steps": steps}


def reranker(state: AgentState) -> dict:
    """Reranker node - merges vector_context and graph_context.

    This node:
    1. Combines results from parallel retrievers
    2. Removes duplicates based on content similarity
    3. Re-scores all results using the rerank API
    4. Outputs unified context list for grader
    """
    question = state["question"]
    vector_context = state.get("vector_context", [])
    graph_context = state.get("graph_context", [])
    temp_context = state.get("temp_context", [])

    steps = ["🔄 Merging retrieval results..."]

    # Combine all results
    all_context = []

    # Add vector results with source tracking
    for ctx in vector_context:
        ctx_copy = ctx.copy()
        ctx_copy["retrieval_source"] = "vector"
        all_context.append(ctx_copy)

    # Add graph results with source tracking
    for ctx in graph_context:
        ctx_copy = ctx.copy()
        ctx_copy["retrieval_source"] = "graph"
        all_context.append(ctx_copy)

    # Add temp results with source tracking
    for ctx in temp_context:
        ctx_copy = ctx.copy()
        ctx_copy["retrieval_source"] = "temp"
        all_context.append(ctx_copy)

    source_counts = f"{len(vector_context)} vector + {len(graph_context)} graph"
    if temp_context:
        source_counts += f" + {len(temp_context)} temp"
    steps.append(f"📊 Found {source_counts} results")


    if not all_context:
        return {
            "context": [],
            "steps": steps + ["⚠️ No context found from any source"],
        }

    # If only one source, skip reranking
    if len(all_context) <= 1:
        return {
            "context": all_context,
            "steps": steps + [f"✅ Using {len(all_context)} result(s) directly"],
        }

    # Remove near-duplicates based on content hash
    seen_content = set()
    unique_context = []
    for ctx in all_context:
        content_hash = hash(ctx.get("content", "")[:200])  # First 200 chars
        if content_hash not in seen_content:
            seen_content.add(content_hash)
            unique_context.append(ctx)

    if len(unique_context) < len(all_context):
        steps.append(f"🔍 Removed {len(all_context) - len(unique_context)} duplicates")

    # Apply unified reranking only if enabled
    if is_rerank_enabled():
        try:
            reranker_model = get_rerank()
            if reranker_model:
                reranked = reranker_model.rerank(
                    query=question,
                    documents=unique_context,
                    top_n=settings.vector_search_results,
                    min_score=settings.min_relevance_score,
                )
                steps.append(f"✅ Reranked to top {len(reranked)} results")
                return {
                    "context": reranked,
                    "steps": steps,
                }
        except Exception as e:
            print(f"⚠️ Rerank failed: {e}")
            steps.append("⚠️ Rerank failed, using original order")
    else:
        steps.append("ℹ️ Rerank disabled, using original order")

    # Fallback: sort by existing score (or if rerank is disabled)
    unique_context.sort(key=lambda x: x.get("score", 0), reverse=True)
    return {
        "context": unique_context[:settings.vector_search_results],
        "steps": steps,
    }


def grader(state: AgentState) -> dict:
    """CRAG pattern - grade if retrieved context is relevant to the question.
    Now includes detailed LLM reasoning in steps for transparency.
    """
    question = state["question"]
    context = state.get("context", [])

    steps = ["🔍 Evaluating context relevance..."]

    if not context:
        return {
            "grade": "insufficient",
            "steps": steps + ["❌ No context retrieved - nothing to evaluate"],
        }

    # Format context for grading (show what we're evaluating)
    context_preview = []
    for i, c in enumerate(context[:3]):
        content = c.get('content', '')[:150]
        source = c.get('source', 'unknown')
        context_preview.append(f"  [{i+1}] {source}: {content}...")

    steps.append(f"📄 Evaluating {len(context)} retrieved items:")
    steps.extend(context_preview)

    # Build the grading prompt - send full content, no truncation
    context_text = "\n\n".join([
        f"[Source {i+1}]: {c.get('content', '')}"
        for i, c in enumerate(context[:5])
    ])


    prompt_template = ChatPromptTemplate.from_template(settings.grader_prompt)
    grade_prompt = prompt_template.format(question=question, context=context_text)

    steps.append(f"🤖 Asking LLM: 'Does this context answer: {question[:50]}...?'")

    llm = get_llm()

    try:
        response = llm.invoke(grade_prompt)
        llm_response = response.content.strip()

        # Show LLM's actual response
        steps.append(f"💬 LLM Response: {llm_response[:200]}")

        is_relevant = "yes" in llm_response.lower()

        if is_relevant:
            return {
                "grade": "relevant",
                "steps": steps + ["✅ Verdict: Context IS relevant to the question"],
            }
        else:
            return {
                "grade": "insufficient",
                "steps": steps + ["⚠️ Verdict: Context may NOT fully address the question"],
            }

    except Exception as e:
        steps.append(f"❌ Grading error: {str(e)[:80]}")
        return {
            "grade": "relevant",  # Default to relevant on error
            "steps": steps + ["⚠️ Defaulting to 'relevant' due to error"],
        }


def generator(state: AgentState) -> dict:
    """Generate final answer from retrieved context.
    Now includes detailed reasoning steps showing LLM interaction.
    """
    question = state["question"]
    context = state.get("context", [])

    steps = ["💡 Generating answer..."]

    # Show what context we're using
    if context:
        steps.append(f"📚 Using {len(context)} context item(s) for answer generation")
        # Show brief context preview
        for i, c in enumerate(context[:2]):
            source = c.get('metadata', {}).get('source', c.get('source', 'unknown'))
            content_preview = c.get('content', '')[:80]
            steps.append(f"  [{i+1}] {source}: {content_preview}...")
    else:
        steps.append("⚠️ No context available - generating from model knowledge")

    # Format context
    context_text = "\n\n".join([
        f"[Source {i+1}]: {c.get('content', '')}"
        for i, c in enumerate(context[:10])
    ])

    # Build prompts from config
    custom_prompt = state.get("custom_prompt")
    system_prompt = custom_prompt if custom_prompt else settings.generator_system_prompt

    # Show prompt info
    if custom_prompt:
        steps.append(f"🎯 Using custom system prompt: {custom_prompt[:50]}...")
    else:
        steps.append("🎯 Using default system prompt")

    steps.append(f"🤖 Sending to LLM: {settings.llm_model}")

    user_prompt_template = ChatPromptTemplate.from_template(settings.generator_user_prompt)
    user_prompt = user_prompt_template.format(question=question, context=context_text)

    llm = get_llm()

    try:
        response = llm.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])

        answer = response.content

        # Show answer length
        steps.append(f"✅ Generated answer ({len(answer)} chars)")

        return {
            "answer": answer,
            "steps": steps,
        }

    except Exception as e:
        steps.append(f"❌ Generation error: {str(e)[:80]}")
        return {
            "answer": f"I encountered an error generating the answer: {str(e)}",
            "steps": steps,
        }


def insufficient_handler(state: AgentState) -> dict:
    """Handle case where context is insufficient."""
    return {
        "answer": "I couldn't find sufficient information to answer your question. Please try rephrasing or provide more context.",
        "steps": ["📝 Providing insufficient data response..."],
    }


def retrieval_evaluator(state: AgentState) -> dict:
    """Evaluate if retrieved context is sufficient to answer the question."""
    question = state.get("question", "")
    vector_context = state.get("vector_context", [])
    temp_context = state.get("temp_context", [])

    # If no context found at all (empty list), definitely insufficient
    if not vector_context and not temp_context:
        return {
            "retrieval_status": "insufficient",
            "steps": ["⚠️ No vector context found, trying Graph RAG..."]
        }

    # Prepare minimal context for LLM check
    samples = []
    if vector_context:
        samples.extend([str(c.get("content", ""))[:300] for c in vector_context[:3]])
    if temp_context:
        samples.extend([str(c.get("content", ""))[:300] for c in temp_context[:2]])

    context_preview = "\n---\n".join(samples)

    prompt = ChatPromptTemplate.from_template(
        """You are a grader assessing whether the retrieved context is sufficient to answer a user question.

        Question: {question}

        Retrieved Context Snippets (Top results):
        {context}

        Does this context contain information RELEVANT to the question that could potentially form an answer?
        Answer YES if it seems relevant.
        Answer NO if it seems completely irrelevant or empty.

        Answer only YES or NO.
        """
    )

    llm = get_langchain_llm()
    chain = prompt | llm

    steps = ["🤔 Evaluating vector retrieval quality..."]
    
    try:
        response = chain.invoke({"question": question, "context": context_preview})
        grade = response.content.strip().upper()

        if "YES" in grade:
            steps.append("✅ Vector context is sufficient, skipping graph search")
            return {
                "retrieval_status": "sufficient",
                "steps": steps
            }
        else:
            steps.append("⚠️ Vector context insufficient, activating Graph Retrieval...")
            return {
                "retrieval_status": "insufficient",
                "steps": steps
            }

    except Exception as e:
        steps.append(f"⚠️ Evaluator error, defaulting to Graph RAG...")
        return {
            "retrieval_status": "insufficient", 
            "steps": steps
        }
