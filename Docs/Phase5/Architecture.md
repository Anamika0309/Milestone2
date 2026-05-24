# Phase 5 — Evaluation, Compliance & Observability: Architecture

**Status**: ✅ Completed & Tested  
**Duration**: 1 day  
**Purpose**: Validate retrieval precision, compliance adherence, and log production runtime.

---

## 5a. Evaluation Harness

### Testing Metrics Suite
- **Factual Accuracy**: pytest checks verifying exact/numeric tolerance on 30+ golden Q&As.
- **Citation Precision**: 100% compliance verifying returned URL contains the exact retrieved fact.
- **Advisory Refusal Rate**: 100% deflection on comparisons, predictions, and recommendations.
- **PII Leakage Rate**: 100% rejection on PII-bearing queries.
- **Formatting Conformance**: 100% validation on <=3 sentence lengths, footer presence, and disclaimer.

---

## 5b. Compliance Gates (CI)

```
Developer Push / PR
       │
       ▼
GitHub Actions Runner
       ├─► 1. Run YAML Schema Linter (sources.yaml, refusal_intents.yaml)
       ├─► 2. Execute Pytest Compliance Suite
       ├─► 3. Run Static Scan for Banned Advisory Keywords in Code
       ├─► 4. Verify FAISS & BM25 Index Freshness
       ▼
   Merge Gate (Blocked if any check fails)
```

---

## 5c. Observability & Operations

### Structured Log Schema
```json
{
  "timestamp": "2026-05-22T01:05:43Z",
  "request_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3d4b6d",
  "query_hash": "sha256:7fec...",
  "resolved_scheme_id": "hdfc_equity",
  "intent_detected": "factual",
  "confidence_score": 0.84,
  "top_chunk_id": "uuid-123",
  "latency_ms": 142,
  "compliance_checks_passed": true
}
```
