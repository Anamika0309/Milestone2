"""
FastAPI UI Backend Server - Phase 4
Exposes endpoints for asking Q&A queries and retrieving scheme/system metadata.
Serves static SPA single-page application elements.
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from mf_faq.orchestrator.service import OrchestratorService
from mf_faq.config import load_sources

# Initialize FastAPI App
app = FastAPI(
    title="Groww Mutual Fund RAG Chatbot API",
    description="REST API for facts-only mutual fund RAG chatbot for HDFC schemes.",
    version="1.0.0"
)

# Initialize Core Orchestrator Service
orchestrator = OrchestratorService()

# Resolve static directory path relative to app.py
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)

# Pydantic schemas for requests/responses
class QueryRequest(BaseModel):
    query: str
    use_groq: Optional[bool] = None

class QueryResponse(BaseModel):
    answer: str
    source_url: Optional[str] = None
    intent: str
    confidence: float
    checks_passed: bool
    scheme_id: Optional[str] = None

@app.get("/health")
async def health_check():
    """Liveness & Readiness probe"""
    return {"status": "healthy"}

@app.get("/meta")
async def get_metadata():
    """Returns corpus freshness, active model, and scheme registry configuration"""
    try:
        sources = load_sources(orchestrator.config_dir)
        schemes_meta = []
        for s in sources.get("schemes", []):
            url = s.get("sources", [{}])[0].get("url", "")
            schemes_meta.append({
                "id": s.get("id"),
                "name": s.get("name"),
                "category": s.get("category"),
                "url": url
            })
        return {
            "title": "Groww Mutual Fund RAG Chatbot",
            "version": "1.0.0",
            "model_engine": "llama-3.3-70b-versatile",
            "schemes": schemes_meta,
            "disclaimer": orchestrator.disclaimer
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading system metadata: {str(e)}")

@app.post("/ask", response_model=QueryResponse)
async def ask_question(req: QueryRequest):
    """Processes Q&A query end-to-end with guardrails and retrievals"""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty")
    
    try:
        res = orchestrator.ask(req.query, use_groq=req.use_groq)
        return QueryResponse(
            answer=res["answer"],
            source_url=res["source_url"],
            intent=res["intent"],
            confidence=res["confidence"],
            checks_passed=res["checks_passed"],
            scheme_id=res["scheme_id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# Expose home route to serve the main HTML file directly
@app.get("/")
async def serve_home():
    """Serves the Single-Page Application index.html"""
    index_path = os.path.join(static_dir, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Frontend index.html not found. Build is incomplete.")
    return FileResponse(index_path)

# Mount the static assets folder at /static
app.mount("/static", StaticFiles(directory=static_dir), name="static")
