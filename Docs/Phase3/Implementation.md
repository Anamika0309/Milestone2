# Phase 3 — Reasoning & Guardrails: Implementation Guide

**Status**: ✅ Implemented & Tested  
**Duration**: 1.5 days

---

## Modules to Implement

| Module | Location | Core Function |
|:--|:--|:--|
| **PII Guard** | `src/mf_faq/orchestrator/pii_guard.py` | Detects Indian PII formats (PAN, Aadhaar, email, phone, OTP) using patterns in `config/pii_patterns.yaml` |
| **Intent Classifier** | `src/mf_faq/orchestrator/intent_classifier.py` | Classifies query into `factual`, `advisory`, `comparison`, or `prediction` |
| **Refusal Composer** | `src/mf_faq/orchestrator/refusal_composer.py` | Composes compliant deflection responses utilizing whitelisted scheme URLs |
| **Generator Adapter** | `src/mf_faq/generation/extractive.py` | Direct sentence synthesis from top-ranked chunk (extractive fallback) |
| **Groq Generator** | `src/mf_faq/generation/groq_caller.py` | Zero-temperature LLM generation grounded strictly on top chunk |
| **Post-Processor** | `src/mf_faq/generation/post_processor.py` | Enforces <=3 sentences, whitelisted URL counts, banned words audit |
| **Orchestration Service** | `src/mf_faq/orchestrator/service.py` | Wires together PII, intent, retrieval, generator, and post-processor |

---

## Standard Response Templates

```python
Templates = {
    'pii_block': (
        "Your query appears to contain personal information. "
        "For your security, I cannot process queries with personal data. "
        "Facts-only. No investment advice."
    ),
    'dont_know_without_link': (
        "I don't have a verified answer for that in my current knowledge base. "
        "Please specify which HDFC scheme you are asking about, and I will try again. "
        "Facts-only. No investment advice."
    ),
    'safe_template': (
        "I was unable to generate a compliant answer for your query. "
        "Please refer to the official scheme page: {url}\n"
        "Facts-only. No investment advice."
    )
}
```

---

## Post-Processor Verification Checklist
1. Tokenize answer body into sentences; truncate to at most 3 sentences if length is exceeded.
2. Check that the URL count matches the required policy (0 for PII/dont_know, 1 for factual/refusal).
3. Validate that any URL cited is string-equal to one of the 5 whitelisted URLs in `sources.yaml`.
4. Scan for advisory keywords. If any banned words match, swap response with `safe_template`.
5. Run defensive PII check on final string to ensure zero leakage.
