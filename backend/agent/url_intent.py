"""URL Intent Detection nodes for LangGraph workflow.

Nodes:
- url_intent_detector: LLM-based detection of URL summarization intent
- direct_url_summarizer: Bypass RAG and summarize URL content directly

This module handles the special case where user wants to simply view/summarize
URL content without a specific query, bypassing the RAG retrieval flow.
"""

import asyncio

from backend.agent.state import AgentState
from backend.ingestion.temp_knowledge import load_urls_with_langchain
from backend.models.llm import get_langchain_llm

# Intent detection prompt
INTENT_DETECTION_PROMPT = """You are an intent classifier. Analyze the user's question and determine if they want a DIRECT URL SUMMARY or a SPECIFIC RAG QUERY.

User question: {question}
Detected URLs: {urls}
Has uploaded files: {has_files}

Classification criteria:
- DIRECT_SUMMARY: User wants to see/summarize/view the URL content without asking a specific question
  Examples: "查看这个网页", "总结一下这个链接", "看看这个URL里有什么", "summarize this page"

- RAG_QUERY: User has a specific question about the URL content
  Examples: "这个网页里有没有AI相关的内容", "find information about pricing", "里面提到了哪些技术"

If the user uploaded files, always use RAG_QUERY.

Respond with ONLY one word: DIRECT_SUMMARY or RAG_QUERY"""

# Direct summary prompt
DIRECT_SUMMARY_PROMPT = """Please summarize the following web page content in a clear and organized manner.
Highlight the key points, main topics, and any important information.

Web page URL: {url}

Content:
{content}

Provide a comprehensive summary in the same language as the content."""


def url_intent_detector(state: AgentState) -> dict:
    """Detect if user wants direct URL summarization or RAG query.

    This node runs FIRST, so it must detect URLs from the question.
    Uses LLM to classify user intent when URLs are detected.
    If no URLs detected, defaults to normal RAG flow.

    Returns:
        dict with url_summarize_direct (bool), detected_urls, and steps
    """
    import re

    question = state["question"]
    temp_files = state.get("temp_files", [])

    steps = ["🔍 Analyzing query intent..."]

    # Detect URLs in question (same pattern as router)
    url_pattern = r"https?://[^\s<>\"')\]]+|www\.[^\s<>\"')\]]+"
    detected_urls = re.findall(url_pattern, question)
    # Clean URLs
    detected_urls = [url.rstrip(".,;:!?") for url in detected_urls]
    detected_urls = list(set(detected_urls))

    # No URLs = normal RAG flow
    if not detected_urls:
        steps.append("📝 No URLs detected, using standard RAG")
        return {
            "url_summarize_direct": False,
            "detected_urls": [],
            "steps": steps,
        }

    steps.append(f"🔗 Found {len(detected_urls)} URL(s) in message")

    # Has temp files = use RAG to search across all content
    if temp_files:
        steps.append("📁 Files uploaded, using RAG for comprehensive search")
        return {
            "url_summarize_direct": False,
            "detected_urls": detected_urls,
            "steps": steps,
        }

    # Use LLM to classify intent
    try:
        llm = get_langchain_llm()
        prompt = INTENT_DETECTION_PROMPT.format(
            question=question,
            urls=", ".join(detected_urls[:3]),
            has_files=bool(temp_files),
        )

        response = llm.invoke(prompt)
        intent = response.content.strip().upper()

        if "DIRECT_SUMMARY" in intent:
            steps.append("🎯 Intent: Direct URL summarization (bypassing RAG)")
            return {
                "url_summarize_direct": True,
                "detected_urls": detected_urls,
                "steps": steps,
            }
        else:
            steps.append("🔍 Intent: Specific query (using RAG retrieval)")
            return {
                "url_summarize_direct": False,
                "detected_urls": detected_urls,
                "steps": steps,
            }

    except Exception as e:
        steps.append(f"⚠️ Intent detection error: {str(e)[:50]}, defaulting to RAG")
        return {
            "url_summarize_direct": False,
            "detected_urls": detected_urls,
            "steps": steps,
        }


def direct_url_summarizer(state: AgentState) -> dict:
    """Fetch URL content and generate summary directly without RAG.

    This bypasses the retrieval flow for simple "view this URL" requests.

    Returns:
        dict with answer and steps
    """
    detected_urls = state.get("detected_urls", [])

    steps = ["📥 Fetching URL content directly..."]

    if not detected_urls:
        return {
            "answer": "No URLs found in your message.",
            "steps": steps,
        }

    # Fetch first URL (limit to avoid overload)
    url = detected_urls[0]
    steps.append(f"🌐 Loading: {url[:50]}...")

    try:
        # Use existing LangChain URL loader
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            url_contents = loop.run_until_complete(load_urls_with_langchain([url]))
        finally:
            loop.close()

        if not url_contents:
            steps.append("❌ Failed to fetch URL content")
            return {
                "answer": f"Unable to fetch content from {url}. The page may be inaccessible or require authentication.",
                "steps": steps,
            }

        # Get content from first result
        content = url_contents[0].get("content", "")[:8000]  # Limit content length
        steps.append(f"✅ Fetched {len(content)} characters")

        # Generate summary with LLM
        steps.append("💡 Generating summary...")
        llm = get_langchain_llm()
        summary_prompt = DIRECT_SUMMARY_PROMPT.format(url=url, content=content)

        response = llm.invoke(summary_prompt)
        answer = response.content

        steps.append("✅ Summary generated successfully")

        return {
            "answer": answer,
            "steps": steps,
            "context": [{
                "content": content[:500] + "...",
                "source": url,
                "source_type": "url_direct",
            }],
        }

    except Exception as e:
        steps.append(f"❌ Error: {str(e)[:100]}")
        return {
            "answer": f"Error processing URL: {str(e)}",
            "steps": steps,
        }
