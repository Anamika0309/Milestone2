# Phase 1 — Ingestion & Corpus Build: Implementation Guide

**Status**: ✅ Completed  
**Module path**: `phases/phase_1/` and `src/mf_faq/ingestion/`

---

## Files Implemented

| File | Location | Status |
|:--|:--|:--|
| `fetcher.py` | `phases/phase_1/fetcher.py` | ✅ Done |
| `extractor.py` | `phases/phase_1/extractor.py` | ✅ Done |
| `cleaner.py` | `phases/phase_1/cleaner.py` | ✅ Done |
| `chunker.py` | `phases/phase_1/chunker.py` | ✅ Done |
| `embedder.py` | `phases/phase_1/embedder.py` | ✅ Done |
| `indexer.py` | `phases/phase_1/indexer.py` | ✅ Done |

---

## Key Design Decisions

1. **DLL-safe imports**: Dynamic DLL check via `is_library_safe()` runs before importing PyTorch/FAISS to prevent silent Windows native crashes.
2. **Atomic Swap Strategy**: Index files are compiled under `.staging/` first. On success, staging is atomically renamed to `data/index/`.
3. **No Scheme Name Pollution in BM25**: Scheme name is only prepended transiently during vector embedding, preventing sparse keyword search dilution.
4. **Stable Content Hash**: Strips NAV, AUM, and date strings before calculating the SHA-256 hash. Ensures live feed updates don't trigger unnecessary re-indexing.

---

## Ingestion CLI Commands

```bash
# Run the complete refresh pipeline (fetch -> extract -> clean -> chunk -> embed -> index)
python -m mf_faq.ingestion.refresh

# Dry-run pipeline execution (no files written to disk)
python -m mf_faq.ingestion.refresh --dry-run

# Rebuild indexes using existing raw HTML snapshots (skips network fetching)
python -m mf_faq.ingestion.refresh --skip-fetch
```

---

## Verification & Status Check

```bash
# Validate that all 5 schemes have non-zero chunk counts in the manifest
python -c "
import json
m = json.load(open('data/index/manifest.json'))
print('Total chunks:', m['n_chunks'])
print('Scheme counts:', m['per_scheme_counts'])
assert len(m['per_scheme_counts']) == 5 and all(v > 0 for v in m['per_scheme_counts'].values())
print('Corpus Validation: PASS')
"
```
