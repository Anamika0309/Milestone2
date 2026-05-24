# Phase 2 — Retrieval Layer: Architecture

**Status**: ✅ Completed  
**Duration**: 1 day  
**Purpose**: Surface the minimum, high-relevance set of chunks to support factual Q&A.

---

## Retrieval Architecture

```
User Query
    │
    ▼
2.1 Query Normalizer
    │  NFKC lowercase, whitespace collapse
    │  Expand MF acronyms: SIP, NAV, ELSS, AUM
    ▼
2.2 Scheme Resolver
    │  Longest-substring match vs whitelisted schemes in sources.yaml
    │  Output: scheme_id or None
    ▼
2.3 Hybrid Retriever
    │  ├─ Dense search  (FAISS, BAAI/bge-small-en, same model as Ingestion)
    │  └─ Sparse search (BM25, same tokenization as Indexer)
    │  → Weighted Reciprocal Rank Fusion (WRRF) → top-10 candidates
    │    • Numeric queries boost BM25 weight to 0.7
    │    • Scheme filter limits chunks to chunk.scheme_id == resolved scheme
    ▼
2.4 Cross-Encoder Re-Ranker
    │  Model: BAAI/bge-reranker-base
    │  Input: top-10 fused candidates
    │  Output: top-3 passages
    │  Fallback: MockCrossEncoder (preserves fusion order) if environment DLL-unsafe
    ▼
2.5 Confidence Gate
    │  If top score < τ (0.7) → "I don't know" path
    │  If margin (top-1 − top-2) < threshold and schemes differ → "I don't know" path
    └─ Else → top-1 chunk forwarded to generation
```

---

## Retrieval Parameters

| Parameter | Default Value | Tuning Scope |
|:--|:--|:--|
| Confidence threshold $	au$ | `0.70` | Balance between false refusals and hallucination risks |
| Dense Search $k$ | `min(20, n_chunks)` | Fixed size based on small whitelisted corpus |
| Sparse Search $k$ | `min(20, n_chunks)` | Matches dense search scope |
| Fusion top-$k$ | `10` | Final candidates forwarded to reranker |
| Reranker Output | `3` | Passed to final generation post-checks |

---

## Exit Criteria
- [x] Top-1 chunk yields correct facts for >= 85% of golden evaluation set queries
- [x] Scheme filter correctly isolates off-scheme facts in targeted queries
- [x] BM25 sparse boost active and functional for numeric-heavy queries (e.g. "1%")
- [x] Windows PyTorch DLL fallback runs gracefully on clean environments
