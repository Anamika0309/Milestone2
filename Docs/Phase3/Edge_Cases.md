# Phase 3 — Reasoning & Guardrails: Edge Cases

**Component**: `pii_guard.py`, `intent_classifier.py`, `refusal_composer.py`, `groq_caller.py`, `post_processor.py`, `service.py`

---

## EC-3.1: Indian PII Pattern False Positive (Legitimate Numbers Blocked)

| | |
|:--|:--|
| **Priority** | 🟠 High |
| **Component** | `pii_guard.py` |

**Trigger**: User submits a legitimate factual query about numeric values (e.g. "Is the exit load 1.25%?" or "Can I start with 500 Rupees?") or references official scheme registration numbers, which are falsely flagged as PII (like PAN cards, Aadhaar, or phone numbers).

**Impact**: Legitimate factual queries are incorrectly deflected as PII, reducing the system's recall.

**Detection**: Logging of PII block triggers; comparison of blocked queries against known factual templates.

**Mitigation**: Use strict word boundaries and length verification in PII regex patterns. Ensure that currency and percentage formats are explicitly whitelisted before PII pattern matching.

---

## EC-3.2: Advisory Query Evading Intent Classifier

| | |
|:--|:--|
| **Priority** | 🔴 Critical |
| **Component** | `intent_classifier.py` |

**Trigger**: A user structures an advisory query using complex wording to bypass standard regex (e.g., "Tell me if this fund is good to buy" or "Will HDFC Mid Cap outperform others over the long term?").

**Impact**: The system generates a subjective/advisory response, violating regulatory facts-only constraints.

**Detection**: Continuous auditing of user queries using a semantic evaluation test suite.

**Mitigation**: Combine regex pattern matching with a lightweight semantic classifier (such as embedding similarity) to detect advisory or speculative intents.

---

## EC-3.3: Confidence Gate Hallucination Pass

| | |
|:--|:--|
| **Priority** | 🔴 Critical |
| **Component** | `confidence_gate.py` |

**Trigger**: A query retrieves a chunk from a different scheme that happens to have a very high semantic score, passing the gate.

**Impact**: Factual inaccuracies where HDFC Mid Cap details are cited for HDFC Equity.

**Detection**: Post-retrieval scheme ID verification (resolver match vs chunk metadata).

**Mitigation**: If a query is resolved to a specific scheme, enforce strict metadata filtering during retrieval. Demote chunks from other schemes by subtracting `0.3` from their score.

---

## EC-3.4: Groq LLM API Outage / Rate Limit

| | |
|:--|:--|
| **Priority** | 🔴 Critical |
| **Component** | `groq_caller.py` |

**Trigger**: Groq API returns HTTP 429 (rate limit) or 503 (service unavailable).

**Impact**: Query generation crashes, returning 500 errors to users.

**Detection**: Exception handling on API requests; latency and error logging.

**Mitigation**: Implement a graceful fallback to extractive-only generation (`extractive.py`), which synthesizes answers directly from the top retrieved chunks without external LLM dependency.

---

## EC-3.5: Post-Processor Rejects Valid Factual Citation

| | |
|:--|:--|
| **Priority** | 🟠 High |
| **Component** | `post_processor.py` |

**Trigger**: Synthesized answer contains valid references that get stripped, or the URL count is incorrectly counted due to format variations.

**Impact**: Factual answer is replaced by the `safe_template` deflection, causing false refusals.

**Detection**: Logging rule trigger counts; automated compliance test suite failures.

**Mitigation**: Explicit parsing of citations and verification using exact whitelist match.

---

## EC-3.6: URL Leakage in Synthesized Answer

| | |
|:--|:--|
| **Priority** | 🔴 Critical |
| **Component** | `post_processor.py` |

**Trigger**: Generator includes external or non-whitelisted URLs (e.g., AMFI or Groww homepage) in the response body.

**Impact**: Governance compliance failure (off-corpus link shown to user).

**Detection**: Strict regex scan of the output string for any URL pattern.

**Mitigation**: Hard substitution of all URLs with the single whitelisted matching Groww URL.

---

## EC-3.7: Generation Exceeds Sentence Limit

| | |
|:--|:--|
| **Priority** | 🟠 High |
| **Component** | `post_processor.py` |

**Trigger**: LLM ignores prompt instructions and generates a long, descriptive 5-sentence response.

**Impact**: Violates strict output formatting limit.

**Detection**: Sentence count validator post-generation.

**Mitigation**: Automated sentence-tokenizing splitter to truncate response at precisely the 3rd sentence.
