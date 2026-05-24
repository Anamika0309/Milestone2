# Phase 1: Ingestion Pipeline — Edge Cases

This document lists all known edge cases specific to the **Phase 1 Ingestion Pipeline** — the complete process of fetching, extracting, cleaning, chunking, embedding, and indexing the 5 HDFC mutual fund scheme pages.

---

## Sub-phase 1.1: Fetcher Edge Cases

### EC-1.1: Robots.txt Blocking

| Field | Detail |
|---|---|
| **ID** | EC-1.1 |
| **Priority** | 🔴 Critical |
| **Component** | `fetcher.py` → `check_robots_txt()` |

**Description**  
Groww updates its `robots.txt` to disallow crawling of the 5 whitelisted fund pages.

**Example Trigger**
```
GET https://groww.in/robots.txt
User-agent: *
Disallow: /mutual-funds/
```

**Impact**  
- Fetcher halts all URL fetching in compliance with robots.txt.  
- Corpus becomes stale; no new data ingested.

**Detection**  
- `robots_allowed = False` returned by `check_robots_txt()`.  
- Corpus freshness timestamp stales beyond configured threshold.

**Mitigation**  
- Halt automated fetching immediately.  
- Alert administrator for manual review and possible negotiation.  
- **Never bypass robots.txt** — governance compliance is mandatory.

---

### EC-1.2: HTTP 429 Rate Limiting

| Field | Detail |
|---|---|
| **ID** | EC-1.2 |
| **Priority** | 🟠 High |
| **Component** | `fetcher.py` → `fetch_with_httpx()` |

**Description**  
Groww's CDN returns HTTP 429 Too Many Requests with a `Retry-After` header, blocking batch fetches.

**Example Trigger**
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

**Impact**  
- Incomplete corpus refresh. Some schemes updated, others skipped.  
- Inconsistent data across 5 schemes.

**Detection**  
- HTTP 429 response code in fetch logs.  
- `fetch_result.success == False` with `error_message` containing "429".

**Mitigation**  
- Respect `Retry-After` header and implement exponential backoff.  
- Default semaphore limit of 2 concurrent requests already in place.  
- Add jitter to retry intervals to avoid synchronized thundering herd.

---

### EC-1.3: ETag Missing or Inconsistent

| Field | Detail |
|---|---|
| **ID** | EC-1.3 |
| **Priority** | 🟡 Medium |
| **Component** | `fetcher.py` → `load_previous_etag()` |

**Description**  
Groww's CDN stops returning `ETag` headers, preventing content-change detection via `If-None-Match`.

**Example Trigger**
```http
HTTP/1.1 200 OK
# No ETag header returned
```

**Impact**  
- Every fetch re-downloads the full page even if content is unchanged.  
- Excessive bandwidth usage; slower refresh cycles.

**Detection**  
- `result.etag is None` for 2+ consecutive fetches.

**Mitigation**  
- Fallback to SHA-256 content hash comparison (`content_hash` in metadata).  
- Alert if hash is unchanged but re-indexing is triggered — skip silently.

---

### EC-1.4: JavaScript-Rendered Content (Playwright Fallback)

| Field | Detail |
|---|---|
| **ID** | EC-1.4 |
| **Priority** | 🟠 High |
| **Component** | `fetcher.py` → `fetch_with_playwright()` |

**Description**  
Groww moves key financial data (expense ratio, exit load tables) behind JS-rendered SPAs, causing `httpx` to return content-empty HTML shells.

**Example Trigger**
```html
<!-- httpx response: no data tables rendered -->
<div id="scheme-details"></div>  <!-- empty, data loaded by JS -->
```

**Impact**  
- Extractor receives empty content.  
- Chunks contain no facts → retrieval returns garbage.

**Detection**  
- Extraction yield for key anchors (expense ratio, exit load) = 0.  
- `content_length < 5000` bytes for a full fund page (unusually small).

**Mitigation**  
- Playwright fallback automatically engaged when httpx result content is too short.  
- Playwright waits for `networkidle` before capturing content.

---

### EC-1.5: Redirect Chains (301/302)

| Field | Detail |
|---|---|
| **ID** | EC-1.5 |
| **Priority** | 🟠 High |
| **Component** | `fetcher.py` |

**Description**  
A whitelisted URL silently redirects to a non-whitelisted URL (e.g., after a Groww site restructure).

**Example Trigger**
```
GET https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
→ 301 Moved Permanently → https://groww.in/mf/hdfc-equity-fund  (NOT whitelisted)
```

**Impact**  
- Content fetched from a non-whitelisted URL.  
- Governance violation — corpus contains content from outside approved sources.

**Detection**  
- `http_status in [301, 302]` logged as a warning in `fetch_single_url()`.

**Mitigation**  
- `follow_redirects=False` set on the httpx client.  
- Any redirect > 0 hops triggers an administrator alert and halts ingestion for that URL.

---

## Sub-phase 1.2: Extractor Edge Cases

### EC-1.6: Missing Must-Have Section Anchors

| Field | Detail |
|---|---|
| **ID** | EC-1.6 |
| **Priority** | 🟠 High |
| **Component** | `extractor.py` |

**Description**  
Key section anchors like "Expense Ratio", "Exit Load", or "Minimum Investment" are missing from the page HTML, possibly due to a redesign.

**Impact**  
- Chunks for those sections are empty or absent.  
- Retrieval returns "I don't know" for those queries.

**Detection**  
- Section extraction health check: flag if fewer than 3 of 6 expected anchors extracted.  
- Log `WARNING: Missing section [expense_ratio]` per scheme.

**Mitigation**  
- Expand selector strategy with multiple fallback CSS/XPath selectors.  
- Use broad text-block fallback if specific anchors are absent.

---

### EC-1.7: Anti-Scraping / CAPTCHA Detection

| Field | Detail |
|---|---|
| **ID** | EC-1.7 |
| **Priority** | 🔴 Critical |
| **Component** | `fetcher.py`, `extractor.py` |

**Description**  
Groww implements bot detection, returning CAPTCHA pages instead of fund data.

**Example Trigger**
```html
<title>Please verify you are human</title>
```

**Impact**  
- Fetcher succeeds (HTTP 200) but extractor receives CAPTCHA HTML.  
- All extracted content is garbage.

**Detection**  
- Extraction yield < 500 characters for a known fund page.  
- Presence of keywords like "captcha", "verify", "robot" in the extracted text.

**Mitigation**  
- Add content validation gate in extractor: reject content containing CAPTCHA indicators.  
- Alert administrator immediately — no automated bypass is allowed.

---

## Sub-phase 1.3: Cleaner Edge Cases

### EC-1.8: Boilerplate Evolution

| Field | Detail |
|---|---|
| **ID** | EC-1.8 |
| **Priority** | 🟡 Medium |
| **Component** | `cleaner.py` |

**Description**  
Groww adds new boilerplate sections (e.g., cookie banners, promotional carousels) that are not in the current strip list.

**Impact**  
- Noisy, irrelevant text added to chunks.  
- Retrieval returns promotional/irrelevant text as answers.

**Detection**  
- Chunk content analysis: high frequency of commercial/marketing keywords.  
- Average chunk length significantly increases.

**Mitigation**  
- Periodically review raw HTML snapshots.  
- Update the boilerplate strip list in `cleaner.py`.

---

### EC-1.9: Currency / Format Standardization Failures

| Field | Detail |
|---|---|
| **ID** | EC-1.9 |
| **Priority** | 🟡 Medium |
| **Component** | `cleaner.py` → `standardize_currency()` |

**Description**  
Groww introduces new currency representations not in the normalisation map (e.g., `INR 500`, `₹500Cr`, `Rupees 500 Crores`).

**Impact**  
- Inconsistent currency strings across chunks.  
- BM25 keyword search fails to match "₹" queries against "INR" text.

**Detection**  
- Currency consistency check across chunks post-cleaning.  
- Presence of multiple currency representations in the same scheme's chunks.

**Mitigation**  
- Expand `currency_map` in `cleaner.py` with new patterns.  
- Add post-clean validation: flag chunks containing unmapped currency strings.

---

## Sub-phase 1.4: Chunker Edge Cases

### EC-1.10: Financial Table Fragmentation

| Field | Detail |
|---|---|
| **ID** | EC-1.10 |
| **Priority** | 🔴 Critical |
| **Component** | `chunker.py` |

**Description**  
A financial data table (e.g., expense ratio by plan type: Direct vs Regular) is split across 2 chunks at the hard-cap boundary, leaving critical context in each half.

**Example**
```
Chunk A: "Expense Ratio | Direct Plan |"  ← cut here
Chunk B: "1.05% | Regular Plan | 1.85%"  ← no header context
```

**Impact**  
- Answer extracted from Chunk B has no plan-type context → factually misleading.

**Detection**  
- Post-chunk integrity: detect chunks containing half-rows (odd `|` counts per line).

**Mitigation**  
- Table-aware chunking: detect Markdown table rows and never split mid-table.  
- Increase soft cap temporarily when a table is detected mid-chunk.

---

### EC-1.11: Single Chunk Exceeds Hard Cap

| Field | Detail |
|---|---|
| **ID** | EC-1.11 |
| **Priority** | 🟡 Medium |
| **Component** | `chunker.py` |

**Description**  
A single extracted section (e.g., a very long scheme details paragraph) exceeds the 400-token hard cap with no sentence boundary to split on.

**Impact**  
- Chunk gets forcibly truncated mid-sentence.  
- Critical facts may be cut off.

**Detection**  
- Token count > 400 in any produced chunk after chunking.

**Mitigation**  
- Force-split at the nearest whitespace or punctuation mark before the hard cap.  
- Log a warning for every hard-cap forced split for review.

---

## Sub-phase 1.5: Embedder Edge Cases

### EC-1.12: Sentence-Transformers DLL Crash (Windows)

| Field | Detail |
|---|---|
| **ID** | EC-1.12 |
| **Priority** | 🔴 Critical |
| **Component** | `embedder.py` → `is_library_safe()` |

**Description**  
On Windows without MSVC Redistributable, importing `sentence_transformers` causes a silent C++ DLL crash that bypasses Python `try/except`, crashing the entire process.

**Impact**  
- Embedder process crashes silently with no error message.  
- No embeddings are generated; indexing fails completely.

**Detection**  
- Subprocess safety check: `is_library_safe("sentence_transformers")` returns `False`.

**Mitigation**  
- All embedding imports are wrapped in `is_library_safe()` subprocess checks.  
- If unsafe, fall back to 384-dimension zero-vector mock embeddings.  
- Log clearly: `"Using mock embedder — sentence-transformers not safe to import"`.

---

### EC-1.13: Embedding Model Version Mismatch

| Field | Detail |
|---|---|
| **ID** | EC-1.13 |
| **Priority** | 🟠 High |
| **Component** | `embedder.py`, `indexer.py` |

**Description**  
The embedding model is updated (e.g., `BAAI/bge-small-en` → `BAAI/bge-small-en-v1.5`) but existing FAISS index was built with the old model's vector space.

**Impact**  
- Query embeddings live in a different vector space than indexed embeddings.  
- Dense search returns completely irrelevant results.

**Detection**  
- Model name/version stored in `indexer.json` manifest.  
- On startup, compare current embedder model name against manifest — mismatch triggers rebuild.

**Mitigation**  
- Always trigger a full re-index when the embedding model changes.  
- Store model name + version hash in `indexer.json`.

---

## Sub-phase 1.6: Indexer Edge Cases

### EC-1.14: FAISS Index Corruption

| Field | Detail |
|---|---|
| **ID** | EC-1.14 |
| **Priority** | 🔴 Critical |
| **Component** | `indexer.py` |

**Description**  
The FAISS `.faiss` binary file becomes corrupted (e.g., partial write during a system crash or disk error).

**Impact**  
- Dense search fails to load → retrieval returns 0 results.  
- System falls back to mock search, degrading answer quality severely.

**Detection**  
- On load, FAISS throws `RuntimeError` or returns invalid dimension.  
- Index file CRC check fails.

**Mitigation**  
- Use atomic write pattern: write to `dense_index.faiss.tmp`, then rename to `dense_index.faiss`.  
- Keep 1 rolling backup of the last successful index build.

---

### EC-1.15: BM25 Index Missing for a Scheme

| Field | Detail |
|---|---|
| **ID** | EC-1.15 |
| **Priority** | 🟠 High |
| **Component** | `indexer.py` |

**Description**  
BM25 index is built successfully but one scheme's chunks are absent because that scheme's fetch failed silently during the same pipeline run.

**Impact**  
- Sparse search returns no results for that scheme's queries.  
- Hybrid fusion is heavily skewed; confidence gate triggers "I don't know" frequently.

**Detection**  
- Post-index health check: verify that all 5 scheme IDs appear in indexed chunk metadata.  
- `indexer.json` manifest reports per-scheme chunk counts.

**Mitigation**  
- Block index commit if any scheme has 0 chunks.  
- Require all 5 schemes to have ≥ 3 chunks before finalizing the index.
