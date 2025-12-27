#!/usr/bin/env python3
"""
Unit test for graph_retriever node function

Run this script to verify graph_retriever works correctly:
    cd /Users/shaneshou/Dev/gts_graph_rag
    uv run python tests/test_graph_retriever.py
"""

import sys
sys.path.insert(0, '.')


def test_get_cypher_chain():
    """Test the cypher chain initialization."""
    print("=" * 60)
    print("Test 1: get_cypher_chain()")
    print("=" * 60)
    
    from backend.agent.nodes import get_cypher_chain
    
    print("\n🔗 Initializing Cypher Chain...")
    chain = get_cypher_chain()
    
    if chain is None:
        print("❌ FAILED: Cypher chain is None")
        return False
    
    print("✅ PASSED: Cypher chain initialized")
    return True


def test_graph_retriever():
    """Test the graph_retriever node function."""
    print("\n" + "=" * 60)
    print("Test 2: graph_retriever()")
    print("=" * 60)
    
    from backend.agent.nodes import graph_retriever
    
    # Create a mock state
    state = {
        "question": "What is BOI?",
        "org_ids": [1],
        "file_ids": None,
        "context": [],
        "steps": [],
        "messages": [],
        "retrieval_source": "hybrid",
        "grade": "",
        "answer": "",
        "custom_prompt": None,
    }
    
    print(f"\n📝 Question: {state['question']}")
    print("\n🔍 Running graph_retriever...")
    
    try:
        result = graph_retriever(state)
        
        print(f"\n📋 Steps returned:")
        for step in result.get("steps", []):
            print(f"   - {step}")
        
        context = result.get("context", [])
        print(f"\n📋 Context items: {len(context)}")
        
        if context:
            for i, ctx in enumerate(context):
                print(f"\n   Context {i+1}:")
                print(f"   - Source: {ctx.get('source', 'N/A')}")
                print(f"   - Cypher: {ctx.get('cypher', 'N/A')[:50]}...")
                content = ctx.get("content", "")
                print(f"   - Content preview: {content[:100]}...")
            print("\n✅ PASSED: graph_retriever returned context")
            return True
        else:
            # Check if it's a connection failure or just no data
            steps = result.get("steps", [])
            if any("failed" in s.lower() or "error" in s.lower() for s in steps):
                print("\n❌ FAILED: Graph retriever encountered an error")
                return False
            else:
                print("\n⚠️ PASSED (with warning): No graph data found, but no errors")
                return True
                
    except Exception as e:
        print(f"\n❌ FAILED: Exception occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_cypher_query():
    """Test a simple cypher query to verify the chain works."""
    print("\n" + "=" * 60)
    print("Test 3: Direct Cypher Chain Query")
    print("=" * 60)
    
    from backend.agent.nodes import get_cypher_chain
    
    chain = get_cypher_chain()
    if chain is None:
        print("❌ FAILED: Cannot get cypher chain")
        return False
    
    print("\n📝 Query: 'What nodes exist in the database?'")
    print("🔍 Executing...")
    
    try:
        result = chain.invoke({"query": "What nodes exist in the database?"})
        
        answer = result.get("result", "")
        print(f"\n📋 Answer: {answer}")
        
        if "intermediate_steps" in result:
            steps = result["intermediate_steps"]
            if steps and len(steps) > 0:
                cypher = steps[0].get("query", "N/A")
                print(f"📋 Generated Cypher: {cypher}")
        
        if answer:
            print("\n✅ PASSED: Query returned a result")
            return True
        else:
            print("\n⚠️ PASSED (with warning): No answer returned")
            return True
            
    except Exception as e:
        print(f"\n❌ FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n🧪 Graph Retriever Unit Tests\n")
    
    results = []
    
    # Test 1: Cypher chain initialization
    results.append(("get_cypher_chain()", test_get_cypher_chain()))
    
    # Test 2: graph_retriever node
    results.append(("graph_retriever()", test_graph_retriever()))
    
    # Test 3: Direct query
    results.append(("Direct Cypher Query", test_simple_cypher_query()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! You can now start the server.")
    else:
        print("⚠️ Some tests failed. Please review the output above.")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
