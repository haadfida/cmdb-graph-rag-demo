"""
graph_retriever.py - Retrieves relevant graph context using vector similarity
Performs cosine similarity search and expands to neighboring nodes
"""
import os
from typing import List, Dict, Any
from neo4j import GraphDatabase
import google.generativeai as genai

# Connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


class GraphRetriever:
    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD, google_api_key=GOOGLE_API_KEY):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        genai.configure(api_key=google_api_key)
        self.embedding_model = "models/embedding-001"

    def close(self):
        self.driver.close()

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding from Google Gemini"""
        result = genai.embed_content(
            model=self.embedding_model,
            content=text,
            task_type="retrieval_query"
        )
        return result['embedding']

    def retrieve(self, question: str, k: int = 5) -> Dict[str, Any]:
        """
        Retrieve relevant graph context for a question

        Args:
            question: User's question
            k: Number of similar nodes to retrieve

        Returns:
            Dictionary with nodes, relationships, and metadata
        """
        # Get question embedding
        question_embedding = self.get_embedding(question)

        with self.driver.session() as session:
            # Vector similarity search
            result = session.run("""
                CALL db.index.vector.queryNodes('nodeEmbedIdx', $k, $queryEmbedding)
                YIELD node, score
                RETURN node, score, id(node) as nodeId
                ORDER BY score DESC
            """, k=k, queryEmbedding=question_embedding)

            similar_nodes = []
            node_ids = []

            for record in result:
                node = record["node"]
                score = record["score"]
                node_id = record["nodeId"]

                node_data = {
                    "id": node_id,
                    "labels": list(node.labels),
                    "properties": dict(node),
                    "score": score
                }
                # Remove embedding from properties (too large)
                node_data["properties"].pop("embedding", None)

                similar_nodes.append(node_data)
                node_ids.append(node_id)

            # Expand to 1-hop neighbors
            if node_ids:
                result = session.run("""
                    MATCH (n)-[r]-(neighbor)
                    WHERE id(n) IN $nodeIds
                    RETURN
                        id(n) as sourceId,
                        id(neighbor) as targetId,
                        type(r) as relType,
                        properties(r) as relProps,
                        neighbor,
                        startNode(r) = n as outgoing
                    LIMIT 50
                """, nodeIds=node_ids)

                relationships = []
                neighbor_nodes = {}

                for record in result:
                    source_id = record["sourceId"]
                    target_id = record["targetId"]
                    rel_type = record["relType"]
                    rel_props = record["relProps"]
                    neighbor = record["neighbor"]
                    is_outgoing = record["outgoing"]

                    # Add relationship
                    relationships.append({
                        "source": source_id if is_outgoing else target_id,
                        "target": target_id if is_outgoing else source_id,
                        "type": rel_type,
                        "properties": rel_props
                    })

                    # Add neighbor node if not already in similar_nodes
                    if target_id not in node_ids and target_id not in neighbor_nodes:
                        neighbor_data = {
                            "id": target_id,
                            "labels": list(neighbor.labels),
                            "properties": dict(neighbor),
                            "score": 0.0  # No score for neighbors
                        }
                        neighbor_data["properties"].pop("embedding", None)
                        neighbor_nodes[target_id] = neighbor_data

                # Combine similar nodes and neighbors
                all_nodes = similar_nodes + list(neighbor_nodes.values())

            else:
                relationships = []
                all_nodes = similar_nodes

        return {
            "nodes": all_nodes,
            "relationships": relationships,
            "question": question,
            "num_similar": len(similar_nodes),
            "num_neighbors": len(neighbor_nodes) if node_ids else 0
        }

    def format_context(self, retrieval_result: Dict[str, Any]) -> str:
        """Format retrieval result as text context for LLM"""
        nodes = retrieval_result["nodes"]
        relationships = retrieval_result["relationships"]

        context_parts = ["# Graph Context\n"]

        # Add nodes
        context_parts.append("## Nodes:")
        for node in nodes:
            labels = ":".join(node["labels"])
            props = node["properties"]
            # Get name or first non-embedding property
            name = props.get("name", props.get(list(props.keys())[0] if props else "unknown"))
            context_parts.append(f"- [{labels}] {name}")
            # Add key properties
            for key, value in props.items():
                if key not in ["name", "embedding", "description"]:
                    context_parts.append(f"  • {key}: {value}")

        # Add relationships
        if relationships:
            context_parts.append("\n## Relationships:")
            for rel in relationships:
                source_node = next((n for n in nodes if n["id"] == rel["source"]), None)
                target_node = next((n for n in nodes if n["id"] == rel["target"]), None)

                if source_node and target_node:
                    source_name = source_node["properties"].get("name", "Node")
                    target_name = target_node["properties"].get("name", "Node")
                    context_parts.append(f"- {source_name} -[{rel['type']}]-> {target_name}")

        return "\n".join(context_parts)


def test_retriever():
    """Test the retriever with sample questions"""
    print("🔍 Testing Graph Retriever\n")

    retriever = GraphRetriever()

    try:
        test_questions = [
            "Where is the DB-Server located?",
            "What assets will break if Web-API goes down?",
            "Who owns Payroll Service?"
        ]

        for question in test_questions:
            print(f"\n❓ Question: {question}")
            result = retriever.retrieve(question, k=3)
            print(f"   Found {result['num_similar']} similar nodes, {result['num_neighbors']} neighbors")

            context = retriever.format_context(result)
            print(f"\n📝 Context:\n{context}\n")
            print("-" * 80)

    finally:
        retriever.close()


if __name__ == "__main__":
    test_retriever()
