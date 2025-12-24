"""
embed_nodes_local.py - Creates vector embeddings using local sentence-transformers
No API calls needed - runs completely offline!
"""
import os
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

# Connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")


class NodeEmbedder:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        print("📥 Loading embedding model (this may take a moment)...")
        # Use a lightweight but effective model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dimension = 384  # This model produces 384-dim vectors

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
        """Get embedding using local model - NO API CALLS!"""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_all_nodes(self):
        """Embed all nodes in the graph"""
        with self.driver.session() as session:
            # First, add Node label to all nodes for the index
            session.run("MATCH (n) SET n:Node")
            print("✓ Added Node label to all nodes")

            # Get all nodes
            result = session.run("MATCH (n) RETURN n, id(n) as nodeId")
            nodes = list(result)

            print(f"\n📝 Embedding {len(nodes)} nodes locally...")

            embedded_count = 0
            for record in nodes:
                node = record["n"]
                node_id = record["nodeId"]

                # Generate description
                description = self.get_node_description(node)

                # Get embedding (locally, no API!)
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
    print("🚀 Creating local embeddings (no API calls!)...\n")

    embedder = NodeEmbedder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    try:
        embedder.embed_all_nodes()
        embedder.create_vector_index()
        embedder.verify_embeddings()
        print("\n✅ Embeddings created successfully!")
    finally:
        embedder.close()


if __name__ == "__main__":
    main()
