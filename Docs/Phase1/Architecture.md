# Phase 1 — Ingestion & Corpus Build: Architecture

**Status**: ✅ Completed  
**Duration**: 1.5 days  
**Purpose**: Convert the 5 whitelisted Groww URLs into a clean, chunked, embedded, queryable corpus.

---

## Ingestion Pipeline Flow

```
Phase 0 sources.yaml (5 URLs)
        │
        ▼
1.1 Fetcher          httpx + Playwright fallback
        │             → data/raw/<scheme_id>/<timestamp>.html
        │             → data/raw/<scheme_id>/meta.json
        ▼
1.2 Extractor        trafilatura + BeautifulSoup
        │             → data/processed/<scheme_id>/extracted.json
        ▼
1.3 Cleaner          NFKC norm + boilerplate strip
        │             → data/processed/<scheme_id>/cleaned.json
        ▼
1.4 Chunker          section-aware, 250 soft / 400 hard token cap
        │             → data/processed/<scheme_id>/chunks.jsonl
        ▼
 1.5 Embedder         BAAI/bge-small-en (384-dim)
        │             → data/index/embeddings.parquet
        │             → data/index/embedder.json
        ▼
 1.6 Indexer          Chroma DB / FAISS (dense) + BM25 (sparse)
        │             → persistent Chroma DB files (or vector.faiss)
        │             → data/index/bm25.pkl
        │             → data/index/chunks.jsonl
        │             → data/index/manifest.json
        ▼
 1.7 Refresh & Health Orchestrator (GitHub Actions cron)
                      → data/index/refresh_log.jsonl
```

---

## Sub-phase Specifications

### 1.1 Fetcher
- **Module**: `src/mf_faq/ingestion/fetcher.py` → `Fetcher.fetch_all()`
- **Tech Stack**: `httpx` primary, `playwright` headless fallback for JS elements
- Respects `robots.txt`; uses ETag `If-None-Match`; exponential backoff on 429
- Never auto-follows 301/302 redirects on whitelisted URLs (governance boundary check)

### 1.2 Extractor
- **Module**: `src/mf_faq/ingestion/extractor.py` → `Extractor.extract(html, scheme_id)`
- **Target Anchors**: Expense Ratio, Exit Load, Scheme Details, Min SIP, Riskometer, Benchmark
- Missing anchors trigger a degraded extraction status.

### 1.3 Cleaner & Normalizer
- **Module**: `src/mf_faq/ingestion/cleaner.py` → `Cleaner.clean(doc)`
- Drops FAQ sections entirely, trims Fund Manager bios
- Normalizes `Rs.` / `INR` → `₹`, applies NFKC whitespace collapse
- Strips volatile fields (live NAV, AUM) for `stable_content_hash` consistency

### 1.4 Chunker
- **Module**: `src/mf_faq/ingestion/chunker.py` → `Chunker.chunk(doc)`
- Soft cap: 250 tokens | Hard cap: 400 tokens | Overlap: 30 tokens
- One HTML section maps to one chunk (never splits tables or facts mid-sentence)

### 1.5 Embedder
- **Module**: `src/mf_faq/ingestion/embedder.py`
- Model: `BAAI/bge-small-en` (384-dim) via `sentence-transformers`
- Embeds `f"{scheme_name}\n\n{text}"` to avoid boilerplate-induced clustering

### 1.6 Indexer
- **Module**: `src/mf_faq/ingestion/indexer.py` (Chroma DB operations are handled via `src/mf_faq/vector_db/chroma_store.py`)
- **Tech Stack**: ChromaDB (persistent vector database) / FAISS (dense) + BM25 (`rank_bm25`) (sparse)
- **Responsibilities**: Stores the generated embeddings in the persistent ChromaDB collection or FAISS flat index, builds the sparse token index, and performs an atomic swap to ensure zero-downtime indexing (builds in staging first).

### 1.7 Refresh & Health Orchestrator
- **Scheduler**: GitHub Actions scheduled workflow (`nightly`/`weekly` UTC cron + `workflow_dispatch` manual dispatch)
- **Secrets Management**: Secure token ingestion and execution using GitHub Secrets (e.g. `GROQ_API_KEY`)
- **Workflow Pipeline Steps**: Checkout code, install Python environment, run pipeline setup, execute fetch/clean/chunk/embed/re-index pipeline (`python -m mf_faq.ingestion.pipeline.run`)
- **Drift Detection**: Automatic content-drift check. Freezes indexing and alerts admin if >=2 URLs change hash simultaneously to avoid indexing layout-level breakages.

---

## Exit Criteria
- [x] All 5 whitelisted URLs fetched and raw HTML saved
- [x] >= 4 critical section anchors extracted successfully per scheme
- [x] Total corpus contains between 30 and 50 chunks (5-12 per scheme)
- [x] Stable content hash matches cleaner output
- [x] Dense and sparse indices successfully built and queryable
