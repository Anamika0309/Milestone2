# Phase 4 — User Interface: Implementation Guide

**Status**: ✅ Completed & Tested  
**Duration**: 0.5 day

---

## Backend Implementation

- **API File**: `src/mf_faq/ui/app.py`
- **Exposed Endpoints**:
  ```python
  from fastapi import FastAPI, HTTPException
  from pydantic import BaseModel
  from mf_faq.orchestrator import Orchestrator

  app = FastAPI(title="Mutual Fund FAQ Assistant API")
  orchestrator = Orchestrator()

  class QueryRequest(BaseModel):
      query: str

  class QueryResponse(BaseModel):
      answer: str
      source_url: str = None
      last_updated: str = None

  @app.post("/ask", response_model=QueryResponse)
  async def ask_question(req: QueryRequest):
      res = orchestrator.ask(req.query)
      return QueryResponse(
          answer=res.answer,
          source_url=res.source_url,
          last_updated=res.last_updated
      )
  ```

---

## Frontend Design Assets

- **Styles**: Defined inside `src/mf_faq/ui/static/index.css`.
  - CSS custom properties for rich dark slate background, neon-blue accent colors, and frosted border card styling.
  - Media queries for responsive layout from 320px mobile screens to wide monitors.
- **Logic**: Defined inside `src/mf_faq/ui/static/index.js`.
  - Form submit interception, spinner showing, template populating, error catch-all.
