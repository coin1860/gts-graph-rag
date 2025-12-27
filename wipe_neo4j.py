from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
username = os.getenv("NEO4J_USERNAME", "neo4j")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE", "neo4j")

if not password:
    print("Error: NEO4J_PASSWORD not found in environment variables")
    exit(1)

driver = GraphDatabase.driver(uri, auth=(username, password))

def wipe_db():
    try:
        with driver.session(database=database) as session:
            print("Cleaning Neo4j database...")
            # Delete all nodes and relationships
            session.run("MATCH (n) DETACH DELETE n")
            print("✅ Neo4j database cleared.")
    except Exception as e:
        print(f"❌ Error clearing Neo4j: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    wipe_db()
