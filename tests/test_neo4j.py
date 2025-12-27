#!/usr/bin/env python3
"""
Test script for Neo4j Graph Retrieval

Run this script to verify Neo4j connection and GraphCypherQAChain work correctly:
    cd /Users/shaneshou/Dev/gts_graph_rag
    uv run python tests/test_neo4j.py
"""

import asyncio
import sys
sys.path.insert(0, '.')

from backend.config import settings


def test_neo4j_connection():
    """Test basic Neo4j connection using langchain-neo4j."""
    print("=" * 60)
    print("Testing Neo4j Connection")
    print("=" * 60)
    
    print(f"\n📍 Neo4j URI: {settings.neo4j_uri}")
    print(f"📍 Username: {settings.neo4j_username}")
    print(f"📍 Database: {settings.neo4j_database}")
    
    try:
        from langchain_neo4j import Neo4jGraph
        
        print("\n🔗 Connecting to Neo4j...")
        graph = Neo4jGraph(
            url=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        
        print("✅ Neo4jGraph connected!")
        
        # Test query
        print("\n📊 Testing query...")
        result = graph.query("RETURN 1 AS test")
        print(f"✅ Query result: {result}")
        
        # Get schema
        print("\n📊 Getting database schema...")
        schema = graph.get_schema
        print(f"Schema preview: {schema[:200] if len(schema) > 200 else schema}...")
        
        return graph
        
    except Exception as e:
        print(f"\n❌ Neo4j connection failed: {type(e).__name__}: {e}")
        return None


def test_cypher_chain(graph):
    """Test GraphCypherQAChain initialization."""
    print("\n" + "=" * 60)
    print("Testing GraphCypherQAChain")
    print("=" * 60)
    
    if graph is None:
        print("⚠️ Skipping - Neo4jGraph not available")
        return None
    
    try:
        from langchain_neo4j import GraphCypherQAChain
        from backend.models.llm import get_langchain_llm
        
        print("\n🔗 Initializing GraphCypherQAChain...")
        llm = get_langchain_llm()
        print(f"   Using LLM: {llm.model_name if hasattr(llm, 'model_name') else 'ChatOpenAI'}")
        
        chain = GraphCypherQAChain.from_llm(
            llm=llm,
            graph=graph,
            verbose=True,
            return_intermediate_steps=True,
            allow_dangerous_requests=True,
        )
        
        print("✅ GraphCypherQAChain initialized!")
        
        # Test simple query
        print("\n📊 Testing Text2Cypher query...")
        result = chain.invoke({"query": "What nodes exist in the database?"})
        
        print(f"\n📋 Result: {result.get('result', 'No result')}")
        if 'intermediate_steps' in result:
            print(f"📋 Generated Cypher: {result['intermediate_steps']}")
        
        return chain
        
    except Exception as e:
        print(f"\n❌ GraphCypherQAChain failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("\n🧪 Neo4j Integration Test\n")
    
    # Test 1: Connection
    graph = test_neo4j_connection()
    
    # Test 2: Cypher Chain
    if graph:
        chain = test_cypher_chain(graph)
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    
    if graph:
        print("✅ Neo4j connection: PASSED")
    else:
        print("❌ Neo4j connection: FAILED")


if __name__ == "__main__":
    main()
