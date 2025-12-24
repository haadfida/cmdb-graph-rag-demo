"""
app.py - FastAPI backend for CMDB Graph RAG
Provides REST API endpoints for question answering
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from rag_chain import CMDBRagChain
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CMDB Graph RAG API",
    description="RAG-based question answering over CMDB knowledge graph",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG chain (singleton)
rag_chain: Optional[CMDBRagChain] = None


class QuestionRequest(BaseModel):
    """Request model for asking questions"""
    question: str


class SourceInfo(BaseModel):
    """Information about a source node"""
    name: str
    type: str
    properties: Dict[str, Any]


class AnswerResponse(BaseModel):
    """Response model for answers"""
    question: str
    answer: str
    sources: List[SourceInfo]
    graph_data: Dict[str, Any]
    error: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize RAG chain on startup"""
    global rag_chain
    try:
        logger.info("Initializing RAG chain...")
        rag_chain = CMDBRagChain()
        logger.info("RAG chain initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG chain: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global rag_chain
    if rag_chain:
        logger.info("Closing RAG chain...")
        rag_chain.close()
        logger.info("RAG chain closed")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CMDB Graph RAG API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    if not rag_chain:
        raise HTTPException(status_code=503, detail="RAG chain not initialized")

    return {
        "status": "healthy",
        "components": {
            "rag_chain": "ok",
            "neo4j": "ok",
            "openai": "ok"
        }
    }


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question about the CMDB

    Args:
        request: Question request containing the user's question

    Returns:
        Answer with sources and graph data for visualization
    """
    if not rag_chain:
        raise HTTPException(status_code=503, detail="RAG chain not initialized")

    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        logger.info(f"Processing question: {request.question}")

        # Get answer from RAG chain
        result = rag_chain.answer(request.question)

        logger.info(f"Answer generated successfully")

        return AnswerResponse(**result)

    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@app.get("/examples")
async def get_example_questions():
    """Get example questions to try"""
    return {
        "examples": [
            "Where is the DB-Server located?",
            "What assets will break if Web-API goes down?",
            "Who owns Payroll Service?",
            "What services are running in Data-Center-1?",
            "Tell me about the Load-Balancer",
            "Which assets depend on the Redis-Cache?",
            "Show me all services owned by John Smith",
            "What is the location of Web-Server-1?"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
