# Phase 2: Retrieval Layer — Edge Cases

This document lists all known edge cases specific to the **Phase 2 Retrieval Layer** — the complete pipeline for normalising queries, resolving schemes, performing hybrid search, reranking candidates, and gating by confidence threshold.

---

## Sub-phase 2.1: Query Normalizer Edge Cases

### EC-2.1: Multi-Language / Mixed-Script Queries

| Field | Detail |
|---|---|
| **ID** | EC-2.1 |
| **Priority** | 🟠 High |
| **Component** | `query_normalizer.py` → `normalize_text()` |

**Description**  
A user submits a query mixing Hindi/Devanagari with English (e.g., `"HDFC का expense ratio kya hai?"`). NFKC normalisation handles Unicode but the tokenizer and acronym expander may produce garbled output.

**Example Trigger**
```
Input: "HDFC का exit load kitna hai?"
→ NFKC output: "hdfc का exit load kitna hai?"
→ MF token expander: "hdfc का exit load kitna hai?" (Hindi words untouched)
```

**Impact**  
- Mixed-language tokens fail BM25 keyword matching.  
- Dense retrieval still works semantically but sparse weight is wasted.

**Detection**  
- Unicode category check: flag queries containing non-Latin scripts after normalisation.

**Mitigation**  
- Detect non-Latin characters post-normalisation, log a warning.  
- Route to dense-only retrieval (sparse weight = 0) for mixed-script queries.

---

### EC-2.2: Overlapping Acronym Expansion

| Field | Detail |
|---|---|
| **ID** | EC-2.2 |
| **Priority** | 🟡 Medium |
| **Component** | `query_normalizer.py` → `expand_mf_tokens()` |

**Description**  
A user query contains an acronym that is both a financial term and a common word (e.g., "SIP" expanded inside "SIPping water" type queries, or NAV overriding a word boundary).

**Example Trigger**
```
Input: "What is the minimum SIP for HDFC?"
→ "sip" → "systematic investment plan"
→ Final: "what is the minimum systematic investment plan for hdfc?"  ✅ Correct

Input: "I am naveen, what is NAV?"
→ "nav" matched inside "naveen" if word boundary not enforced
→ "I am Net Asset Valueen, what is Net Asset Value?"  ❌ Wrong
```

**Impact**  
- Garbled query sent to retrieval, producing irrelevant results.

**Detection**  
- Regex uses `\b` word boundaries — test suite must cover names containing acronyms.

**Mitigation**  
- Enforce strict `\b...\b` word boundaries in all `expand_mf_tokens()` regexes.  
- Add test case: `"naveen"` must not trigger `nav` expansion.

---

### EC-2.3: Empty Query After Normalisation

| Field | Detail |
|---|---|
| **ID** | EC-2.3 |
| **Priority** | 🟠 High |
| **Component** | `query_normalizer.py` |

**Description**  
User submits a query that collapses to an empty string after NFKC normalisation (e.g., query is only emoji, special characters, or whitespace).

**Example Trigger**
```
Input: "   🎉🎊   "
→ After normalize_text(): ""  (empty string)
```

**Impact**  
- Empty string passed to retriever → BM25 scores all 0, dense query embedding = zero vector.  
- Retrieval returns arbitrary top chunks with low confidence.  
- Confidence gate triggers "I don't know" — acceptable but noisy.

**Detection**  
- Post-normalisation check: `len(normalized_query.strip()) == 0`.

**Mitigation**  
- Immediately return a `query_too_short` error response before retrieval.  
- Response: `"Please enter a valid question about mutual fund schemes."` (0 URLs, no disclaimer needed).

---

## Sub-phase 2.2: Scheme Resolver Edge Cases

### EC-2.4: Multi-Scheme Query

| Field | Detail |
|---|---|
| **ID** | EC-2.4 |
| **Priority** | 🟠 High |
| **Component** | `scheme_resolver.py` → `detect_scheme_terms()` |

**Description**  
A user asks a comparative question that inadvertently references two schemes: `"Compare HDFC Mid Cap and HDFC ELSS"`.

**Example Trigger**
```
Input: "Compare HDFC Mid Cap and HDFC ELSS exit load"
→ detected_schemes: ['hdfc_mid_cap', 'hdfc_elss']
```

**Impact**  
- Retriever fetches chunks from both schemes.  
- Hybrid fusion may blend facts from both, producing a confused or mixed answer.  
- The comparison intent itself should have been caught by the intent classifier in Phase 3 as a refusal.

**Detection**  
- `len(detected_schemes) > 1` → flag as potential comparison query.

**Mitigation**  
- When `len(detected_schemes) > 1`, route to advisory/comparison refusal path.  
- Return canned refusal: `"I can only answer factual questions about one specific scheme at a time."` + 1 whitelisted URL.

---

### EC-2.5: Zero Scheme Detected for a Specific Fund Query

| Field | Detail |
|---|---|
| **ID** | EC-2.5 |
| **Priority** | 🟡 Medium |
| **Component** | `scheme_resolver.py` |

**Description**  
User refers to a fund by an uncommon alias not in the alias map (e.g., `"HDFC 80C fund"` for HDFC ELSS Tax Saver).

**Example Trigger**
```
Input: "What is the exit load for HDFC 80C fund?"
→ detected_schemes: []  (no match for "80C")
```

**Impact**  
- Retriever fetches from all 5 schemes' chunks without scheme filtering.  
- Top result may be from the wrong scheme.  
- Answer is technically pulled from a valid chunk but may not be for the intended fund.

**Detection**  
- `len(detected_schemes) == 0` for a query clearly about a specific fund.

**Mitigation**  
- Expand alias map in `scheme_resolver.py` with SEBI/AMFI category names (`80C`, `tax saving fund`, `lock-in fund`).  
- If scheme is ambiguous, include a clarification note in the answer footer.

---

### EC-2.6: Partial Keyword Match — Wrong Scheme Boosted

| Field | Detail |
|---|---|
| **ID** | EC-2.6 |
| **Priority** | 🟡 Medium |
| **Component** | `scheme_resolver.py` |

**Description**  
A common keyword like `"equity"` matches both `HDFC Equity Fund` and `HDFC ELSS` (which is an equity-linked scheme), boosting both incorrectly.

**Example Trigger**
```
Input: "What is the equity allocation of ELSS?"
→ detected_schemes: ['hdfc_equity', 'hdfc_elss']  ← both boosted
```

**Impact**  
- Both schemes' chunks are boosted, diluting the ELSS-specific results.

**Detection**  
- Log multi-scheme matches where scheme detection confidence is ambiguous.

**Mitigation**  
- Apply longest-match priority: `hdfc_elss` matches "elss" (4 chars) vs `hdfc_equity` matches "equity" (6 chars).  
- Boost the scheme with the highest-specificity match only.

---

## Sub-phase 2.3: Hybrid Retriever Edge Cases

### EC-2.7: Dense–Sparse Score Disagreement (High Divergence)

| Field | Detail |
|---|---|
| **ID** | EC-2.7 |
| **Priority** | 🟠 High |
| **Component** | `hybrid_retriever.py` → `fuse_results()` |

**Description**  
Dense search returns Chunk A as top-1 (score=0.92) while sparse BM25 returns Chunk B as top-1 (score=0.88). After WRRF fusion, neither clearly wins.

**Impact**  
- Fused result is a "split decision" — low margin between top-1 and top-2.  
- Confidence gate may trigger "I don't know" even though the correct answer exists.

**Detection**  
- `|dense_rank[i] - sparse_rank[i]| > threshold` for top-3 candidates.

**Mitigation**  
- Log high-divergence events for tuning.  
- For numeric queries (expense ratio, NAV, exit load), increase sparse weight to 0.7 since BM25 is more reliable for exact keyword matches.

---

### EC-2.8: All Results Below Fusion Score Threshold

| Field | Detail |
|---|---|
| **ID** | EC-2.8 |
| **Priority** | 🟠 High |
| **Component** | `hybrid_retriever.py` |

**Description**  
Query is about a topic that exists in the corpus but is phrased so differently that both dense and sparse search return very low scores.

**Example Trigger**
```
Input: "What is the annual maintenance fee for HDFC Mid Cap?"
→ Corpus contains "expense ratio" but not "annual maintenance fee"
→ Dense: max score 0.41 | Sparse: max score 0.28
```

**Impact**  
- Confidence gate blocks the result.  
- User gets "I don't know" despite the answer being in the corpus.

**Detection**  
- Max fused score < 0.5 for a query that was manually verified as answerable.

**Mitigation**  
- Add synonym expansion for known financial term aliases.  
- Include `"annual maintenance fee" → "expense ratio"` in the query normalizer's synonym map.

---

### EC-2.9: Index Not Loaded (Cold Start)

| Field | Detail |
|---|---|
| **ID** | EC-2.9 |
| **Priority** | 🔴 Critical |
| **Component** | `hybrid_retriever.py` → `load_indexes()` |

**Description**  
System starts before the Phase 1 index build has completed (cold start), or `data/index/` is empty/missing.

**Impact**  
- `load_indexes()` returns `False`.  
- All retrievals return empty result lists.  
- Every query gets "I don't know".

**Detection**  
- `vector_store is None` or `indexer.json` missing.  
- Health check on startup reports `health: failed`.

**Mitigation**  
- Block system startup until health check confirms indexes loaded.  
- Return a specific error response: `"System is initialising. Please try again in a few moments."`.

---

## Sub-phase 2.4: Cross-Encoder Reranker Edge Cases

### EC-2.10: Reranker Model Load Failure (Windows DLL)

| Field | Detail |
|---|---|
| **ID** | EC-2.10 |
| **Priority** | 🟠 High |
| **Component** | `cross_encoder_reranker.py` → `_load_model()` |

**Description**  
`BAAI/bge-reranker-base` requires PyTorch C++ DLLs. On Windows without MSVC Redistributable, loading the model crashes silently.

**Example Trigger**
```python
is_library_safe("sentence_transformers")  →  False (DLL crash in subprocess)
→ MockCrossEncoder() is used instead.
```

**Impact**  
- Reranking is performed by mock (returns candidates in original fused order).  
- Precision improvement from reranker is lost.  
- Top-1 chunk may not be the most accurate answer.

**Detection**  
- `CROSS_ENCODER_AVAILABLE = False` in startup logs.  
- Health report: `cross_encoder_available: false`.

**Mitigation**  
- `is_library_safe()` subprocess check prevents the crash.  
- `MockCrossEncoder` cleanly returns candidates ranked by original fused score.  
- Log clearly: `"Cross-encoder unavailable — using fusion-ranked order"`.

---

### EC-2.11: Reranker Reverses Correct Order

| Field | Detail |
|---|---|
| **ID** | EC-2.11 |
| **Priority** | 🟡 Medium |
| **Component** | `cross_encoder_reranker.py` |

**Description**  
The cross-encoder reranks a candidate that contains the correct answer to position 2 or lower, placing a less relevant chunk at top-1.

**Example Trigger**
```
Fused top-1: Chunk A (expense ratio for HDFC Equity: 1.05%)  ✅
After rerank: Chunk B (general HDFC fund overview) at top-1  ❌
→ Answer is now vague overview text instead of the specific fact.
```

**Impact**  
- Top-1 chunk no longer contains the gold answer.  
- Response quality degrades.

**Detection**  
- Evaluation suite: compare reranked top-1 accuracy vs fusion top-1 accuracy.  
- If reranker hurts recall, disable or retune.

**Mitigation**  
- Set reranker as optional (not blocking) — if reranker score < fusion score by > 0.3, prefer fusion ordering.  
- Monitor reranker contribution separately in evaluation.

---

## Sub-phase 2.5: Confidence Gate Edge Cases

### EC-2.12: High Score for an Incorrect Chunk

| Field | Detail |
|---|---|
| **ID** | EC-2.12 |
| **Priority** | 🔴 Critical |
| **Component** | `confidence_gate.py` |

**Description**  
A semantically similar but factually wrong chunk scores above the confidence threshold τ=0.7, passes the gate, and is presented as the answer.

**Example Trigger**
```
Query: "What is the exit load for HDFC Large Cap?"
→ Chunk from HDFC Mid Cap (similar language) scores 0.82
→ Gate passes it → Wrong scheme's exit load returned.
```

**Impact**  
- User receives factually incorrect information presented confidently.  
- Trust in the system is broken.

**Detection**  
- Scheme-ID cross-check: if `chunk.scheme_id != detected_scheme`, flag as mismatch.

**Mitigation**  
- Add **scheme-ID validation gate**: if top chunk's scheme_id doesn't match any detected_scheme from the resolver, demote its score by 0.3 before passing to confidence gate.

---

### EC-2.13: Narrow Margin — Both Answers Different Facts

| Field | Detail |
|---|---|
| **ID** | EC-2.13 |
| **Priority** | 🟠 High |
| **Component** | `confidence_gate.py` → `filter_by_confidence()` |

**Description**  
Top-1 score = 0.72 and top-2 score = 0.70 (margin = 0.028), both about different schemes. The gate allows top-1 through since score ≥ τ, but margin is razor thin.

**Impact**  
- Near-coin-flip between two different scheme facts.  
- Confidence in the answer is artificially high.

**Detection**  
- `(top_score - second_score) / top_score < low_margin_threshold (0.2)` AND different scheme IDs.

**Mitigation**  
- When margin < `low_margin_threshold` AND the two chunks are from different schemes, override to "I don't know" response.  
- Log as `EC-2.13: Narrow margin cross-scheme ambiguity`.

---

### EC-2.14: Threshold Too Strict — All Answerable Queries Blocked

| Field | Detail |
|---|---|
| **ID** | EC-2.14 |
| **Priority** | 🟡 Medium |
| **Component** | `confidence_gate.py` |

**Description**  
If τ is set too high (e.g., 0.9), even good retrieval results are blocked, producing excessive "I don't know" responses.

**Example**
```
τ = 0.9
→ Correct chunk score: 0.78 → blocked → "I don't know" returned incorrectly.
```

**Impact**  
- System appears broken even with a correctly built corpus.  
- User satisfaction drops sharply.

**Detection**  
- Evaluation suite: "I don't know" rate > 20% on golden factual query set.

**Mitigation**  
- Default τ = 0.7 (empirically tuned).  
- Expose τ as a configurable parameter; re-tune with eval suite whenever corpus changes significantly.  
- Target: "I don't know" rate < 10% on known-answerable queries.
