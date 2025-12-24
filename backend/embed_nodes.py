"""
embed_nodes.py - Creates vector embeddings for all nodes in the graph
Uses Google Gemini embeddings API and stores vectors in Neo4j
"""
import os
import time
from neo4j import GraphDatabase
import google.generativeai as genai

# Connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required")


class NodeEmbedder:
    def __init__(self, uri, user, password, google_api_key):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        genai.configure(api_key=google_api_key)
        self.embedding_model = "models/embedding-001"
        self.embedding_dimension = 768  # Gemini embedding-001 produces 768-dim vectors

    def close(self):
        self.driver.close()

    def create_vector_index(self):
        """Create a vector index for similarity search"""
        with self.driver.session() as session:
            # Drop existing index if it exists
            try:
                session.run("DROP INDEX nodeEmbedIdx IF EXISTS")
            except:
                pass

            # Create new vector index
            session.run(f"""
                CREATE VECTOR INDEX nodeEmbedIdx IF NOT EXISTS
                FOR (n:Node)
                ON n.embedding
                OPTIONS {{
                    indexConfig: {{
                        `vector.dimensions`: {self.embedding_dimension},
                        `vector.similarity_function`: 'cosine'
                    }}
                }}
            """)
            print("✓ Vector index created")

    def get_node_description(self, node):
        """Generate a text description from node properties"""
        label = list(node.labels)[0] if node.labels else "Node"
        props = dict(node)

        # Format properties as readable text
        prop_parts = [f"{key}: {value}" for key, value in props.items() if key != 'embedding']
        prop_text = ", ".join(prop_parts)

        return f"{label} - {prop_text}"

    def get_embedding(self, text):
        """Get embedding from Google Gemini with retry logic"""
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                result = genai.embed_content(
                    model=self.embedding_model,
                    content=text,
                    task_type="retrieval_document"
                )
                return result['embedding']
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        print(f"  ⚠️  Rate limit hit, waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise
                else:
                    raise

    def embed_all_nodes(self):
        """Embed all nodes in the graph"""
        with self.driver.session() as session:
            # First, add Node label to all nodes for the index
            session.run("MATCH (n) SET n:Node")
            print("✓ Added Node label to all nodes")

            # Get all nodes
            result = session.run("MATCH (n) RETURN n, id(n) as nodeId")
            nodes = list(result)

            print(f"\n📝 Embedding {len(nodes)} nodes...")

            embedded_count = 0
            for record in nodes:
                node = record["n"]
                node_id = record["nodeId"]

                # Generate description
                description = self.get_node_description(node)

                # Get embedding with rate limiting
                embedding = self.get_embedding(description)

                # Store embedding back to node
                session.run("""
                    MATCH (n)
                    WHERE id(n) = $nodeId
                    SET n.embedding = $embedding
                    SET n.description = $description
                """, nodeId=node_id, embedding=embedding, description=description)

                embedded_count += 1
                if embedded_count % 5 == 0:
                    print(f"  Embedded {embedded_count}/{len(nodes)} nodes...")

                # Add delay to respect rate limits (Gemini free tier: ~2 requests/min)
                if embedded_count < len(nodes):
                    time.sleep(2)

            print(f"✓ All {embedded_count} nodes embedded successfully")

    def verify_embeddings(self):
        """Verify embeddings were created"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n:Node)
                WHERE n.embedding IS NOT NULL
                RETURN count(n) as embeddedCount
            """)
            count = result.single()["embeddedCount"]
            print(f"\n✅ Verification: {count} nodes have embeddings")

            # Show sample
            result = session.run("""
                MATCH (n:Node)
                WHERE n.description IS NOT NULL
                RETURN n.description as description
                LIMIT 5
            """)
            print("\n📋 Sample descriptions:")
            for record in result:
                print(f"  • {record['description']}")


def main():
    print("🚀 Creating embeddings for all nodes...\n")

    embedder = NodeEmbedder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, GOOGLE_API_KEY)

    try:
        embedder.embed_all_nodes()
        embedder.create_vector_index()
        embedder.verify_embeddings()
        print("\n✅ Embeddings created successfully!")
    finally:
        embedder.close()


if __name__ == "__main__":
    main()
