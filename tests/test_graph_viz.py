"""
Test format_neo4j_to_viz function with field-based Cypher.
"""
import os
from dotenv import load_dotenv

load_dotenv()

def test_format_neo4j():
    print("=" * 60)
    print("Test: format_neo4j_to_viz (field-based)")
    print("=" * 60)
    
    try:
        from langchain_neo4j import Neo4jGraph
        
        graph = Neo4jGraph(
            url=os.getenv("NEO4J_URI"),
            username=os.getenv("NEO4J_USERNAME"),
            password=os.getenv("NEO4J_PASSWORD"),
        )
        print(f"✅ Connected to Neo4j")
        
        # Test the exact Cypher that LLM generates
        cypher = "MATCH (d:Document) WHERE d.text CONTAINS 'shane' RETURN d.id, d.text, d.org_id, d.source, d.source_doc_id LIMIT 3"
        print(f"\n📊 Query: {cypher}")
        
        raw_result = graph.query(cypher)
        print(f"\n📋 Raw result ({len(raw_result)} records):")
        for i, r in enumerate(raw_result):
            print(f"  Record {i}:")
            for k, v in r.items():
                print(f"    {k}: {str(v)[:50]}...")
        
        # Test format function with field detection
        def format_neo4j_to_viz(records):
            nodes = []
            links = []
            node_ids = set()
            
            for record in records:
                if isinstance(record, dict):
                    has_field_keys = any('.' in str(k) for k in record.keys())
                    
                    if has_field_keys:
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
                            })
                    else:
                        for key, value in record.items():
                            if isinstance(value, dict):
                                nid = value.get("id", value.get("name"))
                                if nid and nid not in node_ids:
                                    node_ids.add(nid)
                                    nodes.append({"id": str(nid), "label": str(nid)[:30], "type": key})
            
            if len(nodes) > 1:
                for i in range(len(nodes) - 1):
                    links.append({"source": nodes[i]["id"], "target": nodes[i + 1]["id"], "label": "RELATED"})
            
            return {"nodes": nodes, "links": links}
        
        viz_data = format_neo4j_to_viz(raw_result)
        
        print(f"\n📊 Formatted viz data:")
        print(f"  Nodes ({len(viz_data['nodes'])}):")
        for n in viz_data['nodes']:
            print(f"    - {n}")
        print(f"  Links ({len(viz_data['links'])}):")
        for l in viz_data['links']:
            print(f"    - {l}")
        
        print("\n✅ Test completed!")
        
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_format_neo4j()

