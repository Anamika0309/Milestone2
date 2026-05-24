# Phase 2 — Retrieval Layer: Implementation Guide

**Status**: ✅ Completed  
**Module path**: `phases/phase_2/` and `src/mf_faq/retrieval/`

---

## Files Implemented

| File | Status | Notes |
|:--|:--|:--|
| `query_normalizer.py` | ✅ Done | Unicode NFKC normalization + acronym expansion (`SIP`, `NAV`, `ELSS`, `AUM`) |
| `scheme_resolver.py` | ✅ Done | Substring NER resolver + `resolve_schemes()` backward compatibility |
| `hybrid_retriever.py` | ✅ Done | FAISS + BM25 + Reciprocal Rank Fusion (RRF) |
| `cross_encoder_reranker.py` | ✅ Done | BGE reranker adapter with DLL-safe Mock fallback |
| `confidence_gate.py` | ✅ Done | Threshold score check + `filter_results()` compatibility wrapper |
| `__init__.py` | ✅ Done | Retrieval module exports |

---

## Key Implementation Highlights

1. **Numeric Queries Sparse Boosting**: If the normalized query contains numbers, `%`, or currency symbols (`₹`), the BM25 sparse search weight in Reciprocal Rank Fusion is automatically boosted to `0.7` to ensure precise numeric matching.
2. **Ambiguity Demotion**: Chunks that belong to a scheme other than the resolved scheme are penalized by subtracting `0.3` from their score before passing the confidence gate.
3. **Mock Fallbacks**: If PyTorch or FAISS imports fail (common in Windows environments without MSVC runtimes), the system automatically initializes mock semantic searchers and mock rerankers that preserve keyword-based BM25 ordering.

---

## Running Retrieval Demo

```bash
# Query the retrieval system from the command line
python -m mf_faq.retrieval "What is the exit load of HDFC Equity Fund?"
```
