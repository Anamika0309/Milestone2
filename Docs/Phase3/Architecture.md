# Phase 3 — Reasoning & Guardrails: Architecture

**Status**: ✅ Implemented & Tested  
**Duration**: 1.5 days  
**Purpose**: Securely translate queries and retrieved chunks into compliant, single-sourced, facts-only answers.

---

## Guardrails & Reasoning Pipeline

```
User Query
    │
    ▼
[ PII Guard ] ────► Yes ────► pii_block template (0 URLs, zero-retrieval)
    │ No
    ▼
[ Intent Classifier ] ──► Non-Factual ──► Refusal Composer (canned copy + 1 scheme URL)
    │ Factual
    ▼
Phase 2 Retrieval Layer
    │ Top-3 chunks
    ▼
[ Confidence Gate ] ────► Fail (<0.7) ────► dont_know_without_link (0 URLs)
    │ Pass (>=0.7)
    ▼
[ Generator Stack ] ──► Extractive (default) OR Groq LLM (low-temperature prompt)
    │ Draft answer
    ▼
[ Post-Processor ] ──► Fail ──► safe_template fallback (1 whitelisted URL)
    │ All checks pass
    ▼
Final Compliant Response (<=3 sentences + 1 whitelisted URL + Date footer)
```

---

## URL Policy Enforcement Matrix

| Situation | URLs Allowed | Response Format |
|:---|:---|:---|
| PII detected | **Exactly 0** | `pii_block` template (strictly 0 URLs to prevent any link exposure for sensitive/personal context) |
| Insufficient evidence / low confidence | **Exactly 0** | `dont_know_without_link` template (strictly 0 URLs to ensure ungrounded queries do not point to any resource) |
| Advisory / comparison refusal | **Exactly 1** | Canned copy + matching whitelisted scheme URL |
| Factual answer success | **Exactly 1** | Synthesized fact body + `source_url` from chunk |

> [!IMPORTANT]
> **Zero URL Policy for PII & "I Don't Know"**:
> To ensure absolute safety and privacy, if a query is rejected due to PII detection or if retrieval confidence is too low to formulate a factual answer ("I don't know"), the assistant's reply **MUST NOT contain any URL**. This completely eliminates the risk of linking sensitive personal contexts or incorrect/misleading sources.


---

## Output Compliance Standards
1. **Sentence Limit**: Factual answer body must contain at most 3 sentences (excluding citations/footers).
2. **Banned Words**: Any presence of banned tokens (`recommend`, `invest`, `outperform`, `better than`, `best fund`) triggers immediate fallback.
3. **Footer Format**: Must end with `Last updated from sources: YYYY-MM-DD`.
