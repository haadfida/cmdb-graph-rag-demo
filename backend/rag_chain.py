"""
rag_chain.py - LangGraph-based RAG chain for CMDB question answering
Orchestrates: Question -> Retrieve -> Generate Answer
"""
import os
from typing import TypedDict, Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from graph_retriever_local import GraphRetriever
from simple_llm import generate_answer

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
USE_SIMPLE_LLM = os.getenv("USE_SIMPLE_LLM", "false").lower() == "true"


class GraphState(TypedDict):
    """State that flows through the graph"""
    question: str
    retrieval_result: dict
    context: str
    answer: str
    error: str | None


class CMDBRagChain:
    """RAG Chain for CMDB question answering using LangGraph"""

    def __init__(self, model_name: str = "gemini-pro"):
        self.retriever = GraphRetriever()
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            google_api_key=GOOGLE_API_KEY,
            convert_system_message_to_human=True  # Gemini doesn't support SystemMessage
        )
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("generate", self._generate_node)

        # Add edges
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()

    def _retrieve_node(self, state: GraphState) -> GraphState:
        """Retrieve relevant graph context"""
        question = state["question"]

        try:
            # Perform vector similarity search + expand to neighbors
            retrieval_result = self.retriever.retrieve(question, k=5)

            # Format as text context
            context = self.retriever.format_context(retrieval_result)

            return {
                **state,
                "retrieval_result": retrieval_result,
                "context": context,
                "error": None
            }
        except Exception as e:
            return {
                **state,
                "error": f"Retrieval error: {str(e)}"
            }

    def _generate_node(self, state: GraphState) -> GraphState:
        """Generate answer using LLM or simple fallback"""
        if state.get("error"):
            return state

        question = state["question"]
        context = state["context"]

        try:
            # Use simple LLM fallback if enabled or if Gemini fails
            if USE_SIMPLE_LLM:
                answer = generate_answer(question, context)
                return {
                    **state,
                    "answer": answer,
                    "error": None
                }

            # Try Gemini API
            system_prompt = """You are a helpful CMDB (Configuration Management Database) assistant.
You have access to a knowledge graph containing information about IT assets, services, users, and their relationships.

Your task is to answer questions based on the provided graph context. Be specific and reference the entities and relationships mentioned in the context.

If the context doesn't contain enough information to answer the question, say so clearly.

Keep your answers concise and factual."""

            user_prompt = f"""Graph Context:
{context}

Question: {question}

Please provide a clear, concise answer based on the graph context above."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = self.llm.invoke(messages)
            answer = response.content

            return {
                **state,
                "answer": answer,
                "error": None
            }
        except Exception as e:
            # Fallback to simple LLM on error
            print(f"Gemini API failed, using simple fallback: {str(e)}")
            answer = generate_answer(question, context)
            return {
                **state,
                "answer": answer,
                "error": None
            }

    def answer(self, question: str) -> dict:
        """
        Answer a question using RAG over the graph

        Args:
            question: User's question

        Returns:
            Dictionary with answer, sources, and metadata
        """
        # Initialize state
        initial_state = {
            "question": question,
            "retrieval_result": {},
            "context": "",
            "answer": "",
            "error": None
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        # Check for errors
        if final_state.get("error"):
            return {
                "question": question,
                "answer": f"Error: {final_state['error']}",
                "sources": [],
                "graph_data": {},
                "error": final_state["error"]
            }

        # Extract sources from retrieval result
        retrieval_result = final_state.get("retrieval_result", {})
        nodes = retrieval_result.get("nodes", [])

        sources = []
        for node in nodes:
            if node.get("score", 0) > 0:  # Only include similar nodes, not neighbors
                labels = ":".join(node["labels"])
                props = node["properties"]
                name = props.get("name", "Unknown")
                sources.append({
                    "name": name,
                    "type": labels,
                    "properties": props
                })

        result = {
            "question": question,
            "answer": final_state.get("answer", ""),
            "sources": sources,
            "graph_data": retrieval_result or {},  # For visualization
            "error": None
        }

        # Debug logging
        print(f"DEBUG - Final result keys: {result.keys()}")
        print(f"DEBUG - graph_data type: {type(result['graph_data'])}")

        return result

    def close(self):
        """Clean up resources"""
        self.retriever.close()


def test_chain():
    """Test the RAG chain with sample questions"""
    print("🤖 Testing CMDB RAG Chain\n")

    chain = CMDBRagChain()

    try:
        test_questions = [
            "Where is the DB-Server located?",
            "What assets will break if Web-API goes down?",
            "Who owns Payroll Service?",
            "What services are running in Data-Center-1?",
            "Tell me about the Load-Balancer"
        ]

        for question in test_questions:
            print(f"\n❓ Question: {question}")
            result = chain.answer(question)

            print(f"\n💬 Answer: {result['answer']}")

            if result["sources"]:
                print(f"\n📚 Sources:")
                for source in result["sources"]:
                    print(f"  • {source['type']}: {source['name']}")

            print("\n" + "=" * 80)

    finally:
        chain.close()


if __name__ == "__main__":
    test_chain()
