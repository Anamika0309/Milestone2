# Phase 4 — User Interface: Architecture

**Status**: ✅ Completed & Tested  
**Duration**: 0.5 day  
**Purpose**: Sleek, trustworthy, responsive web interface for factual mutual fund assistant.

---

## Interface Layout & Design

```
┌──────────────────────────────────────────────────────────────┐
│  Mutual Fund FAQ Assistant                                   │
│  Facts-only. No investment advice.            [disclaimer]   │
├──────────────────────────────────────────────────────────────┤
│  Welcome! Ask a factual question about HDFC schemes.        │
│                                                              │
│  Try one of these:                                           │
│   • What is the expense ratio of HDFC Equity Fund?          │
│   • What is the exit load of HDFC Mid Cap Fund?             │
│   • What is the lock-in period for ELSS fund?               │
├──────────────────────────────────────────────────────────────┤
│  [  type your question…                                ] [→] │
├──────────────────────────────────────────────────────────────┤
│  Answer area                                                 │
│  ─ short answer (≤3 sentences)                               │
│  ─ Source: <single clickable link>                           │
│  ─ Last updated from sources: <date>                         │
└──────────────────────────────────────────────────────────────┘
```

---

## Technical Stack

### Backend API (`FastAPI`)
- `POST /ask`: Receives user query, passes to Orchestrator, returns structured JSON.
- `GET /meta`: Returns corpus freshness, active model, and scheme registry.
- `GET /health`: Standard Liveness/Readiness probe.

### Frontend SPA (Vanilla JS + HTML5 + CSS3)
- Fully self-contained single-page application (SPA).
- **Aesthetic**: Modern sleek glassmorphism dashboard, harmonized dark mode palette, Inter font family.
- **Interactions**: Subtle hover micro-animations, loading animations, auto-disabled submit during pending fetch calls.

---

## Security & Compliance Rules
- **No Login / PII collection**: Zero inputs saved or logged; queries containing PII are deflected locally before transmission if possible.
- **Strict Citation Target**: Citations rendered as clickable anchor tags with `target="_blank" rel="noopener nofollow"`.
