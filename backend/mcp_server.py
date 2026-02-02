"""FastMCP server for GTS Graph RAG.

Provides MCP tools for GitHub Copilot and other MCP clients to:
1. rag_chat - Full RAG conversation with LLM-generated answers
2. search_knowledge - Return top K knowledge snippets for external LLM summarization

Uses shared rag_service module for core functionality.
"""

from fastmcp import FastMCP

from backend.config import settings
from backend.database import SessionLocal
from backend.crud.organization import get_organization_by_name
from backend.services.rag_service import (
    run_rag_query,
    search_vector_store,
    format_knowledge_for_llm,
)


# Create MCP server
mcp = FastMCP(
    "GTS RAG Knowledge Server",
    instructions="RAG knowledge server powered by GTS Graph RAG system. Provides tools for knowledge search and RAG-based question answering.",
)


def get_org_ids_for_mcp() -> list[int]:
    """Get organization IDs for MCP requests.
    
    Uses the default organization configured in settings.
    Returns empty list if organization not found.
    """
    db = SessionLocal()
    try:
        org = get_organization_by_name(db, settings.mcp_default_org)
        if org:
            return [org.id]
        return []
    finally:
        db.close()


@mcp.tool
async def rag_chat(question: str) -> str:
    """
    使用 RAG 系统回答问题。
    
    系统会搜索知识库，找到相关文档片段，使用知识图谱增强，
    然后使用 LLM 生成综合答案。
    
    Args:
        question: 用户的问题
        
    Returns:
        基于知识库内容生成的答案
    """
    try:
        org_ids = get_org_ids_for_mcp()
        if not org_ids:
            return f"错误：默认组织 '{settings.mcp_default_org}' 不存在。请联系管理员创建该组织。"
        
        # Use shared RAG service
        answer = await run_rag_query(
            question=question,
            org_ids=org_ids,
        )
        
        return answer if answer else "抱歉，无法根据知识库生成答案。"
        
    except Exception as e:
        return f"RAG 查询出错: {str(e)}"


@mcp.tool
async def search_knowledge(question: str, top_k: int = 3) -> str:
    """
    在知识库中搜索相关片段，返回原始知识片段供外部 LLM 总结。
    
    适用于 GitHub Copilot 等外部 LLM，减少内部 API token 调用。
    系统会对问题进行 embedding，在向量库中搜索最相关的知识片段。
    
    Args:
        question: 搜索查询
        top_k: 返回的知识片段数量，默认 3
        
    Returns:
        包含 RAG 提示和知识片段的格式化文本
    """
    try:
        org_ids = get_org_ids_for_mcp()
        if not org_ids:
            return f"错误：默认组织 '{settings.mcp_default_org}' 不存在。请联系管理员创建该组织。"
        
        # Use shared vector search service
        snippets = search_vector_store(
            question=question,
            org_ids=org_ids,
            top_k=min(top_k, settings.mcp_search_top_k),
        )
        
        # Format for external LLM
        return format_knowledge_for_llm(question, snippets)
        
    except Exception as e:
        return f"知识搜索出错: {str(e)}"


# Export mcp instance for mounting
__all__ = ["mcp"]
