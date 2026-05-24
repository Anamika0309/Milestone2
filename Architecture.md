# Mutual Fund FAQ Assistant — Phase-wise Architecture

Companion design document to `Problem_Statement.md`. Goal: a facts-only, source-cited, RAG-based Q&A assistant for mutual fund schemes (Groww context). Iteration scope: the corpus is strictly the 5 Groww HDFC scheme URLs listed in Phase 0 — no other URLs are ingested or cited.

---

## 1. Architectural Principles

These principles drive every phase below:

1. **Facts-over-Intelligence** — retrieval grounds every answer; the Groq-hosted generation model only reformats retrieved facts (optional path; default remains extractive).
2. **Single source of truth per answer** — exactly one citation URL per response.
3. **Closed corpus** — only whitelisted official URLs are ingested; nothing else can leak in.
4. **Refusal by default** — advisory / opinion queries are deflected with a polite, educational redirect.
5. **PII-free** — no PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers are collected, logged, or processed.
6. **Determinism > Creativity** — low temperature, strict prompt contracts, hard answer-length caps (≤ 3 sentences).
7. **Auditability** — every response is traceable to a chunk, a document, a source URL, and a "last updated" timestamp.

---

## 2. Phase-wise Architecture

The build is structured in 6 phases, each phase producing a working, demoable artifact.

---

## Phase 0 — Foundation & Governance

**Purpose**: lock down scope, sources, and guardrails before writing code.

### 🔒 Locked Corpus — Exactly These 5 URLs, Nothing Else

> [!CAUTION]
> **For this project, we will use ONLY the following 5 URLs — exactly as written below. No other URLs are to be ingested, processed, fetched, embedded, indexed, or cited under any circumstance.**
> - No AMC PDFs (KIM / SID / factsheets)
> - No AMFI pages
> - No SEBI pages
> - No AMC website FAQ pages
> - No other Groww pages beyond these 5
>
> Every fact the assistant returns must trace back to exactly one of these 5 URLs. Every citation must be one of these 5 URLs — verbatim, string-equal. This constraint is enforced by `sources.yaml` and by the Phase 3 post-processor whitelist check.

```
https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
```

- **Selected AMC**: HDFC Mutual Fund (HDFC Asset Management Company Ltd.)
- **Selected Schemes (5, category-diverse)** — these 5 Groww URLs are the entire corpus for this project. No other URLs are used.

| # | Scheme | Category | Source URL (Groww) |
|:--|:--|:--|:--|
| 1 | HDFC Mid Cap Fund — Direct Growth | Mid Cap | `https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth` |
| 2 | HDFC Equity Fund — Direct Growth | Flexi Cap | `https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth` |
| 3 | HDFC Focused Fund — Direct Growth | Focused | `https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth` |
| 4 | HDFC ELSS Tax Saver — Direct Plan Growth | ELSS | `https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth` |
| 5 | HDFC Large Cap Fund — Direct Growth | Large Cap | `https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth` |

### Citation Rule (enforced by Phase 3 post-processor)

- The cited URL must be exactly one of the 5 URLs above (string-equal match against `sources.yaml`).
- If no chunk from these 5 URLs supports the query at the confidence threshold (or if the query contains personal information/PII) → respond with the "I don't know" or PII-block template with **zero URLs** (`dont_know_without_link` or `pii_block`).
- For refusals of advisory/comparison/prediction queries → the "educational link" returned is the Groww scheme page most relevant to the query (or a generic one of the 5 if no scheme is detected). No off-corpus link (AMFI/SEBI/etc.) is ever returned.


### What the assistant explicitly cannot answer in this iteration

- Tax-statement / capital-gains download walkthroughs (AMC help pages not ingested).
- Deep regulatory definitions sourced from AMFI/SEBI explainers.
- Anything sourced from KIM/SID PDFs that isn't already surfaced on the Groww product page.

For these, the assistant returns the "I don't have a verified answer" response with the relevant Groww scheme link.

### Deliverables

- `config/sources.yaml` — the 5-URL registry; metadata: `{scheme_id, doc_type, last_updated, content_hash}`.
- `config/refusal_intents.yaml` — patterns + canned refusal copy (educational link is always one of the 5 Groww URLs).
- `config/pii_patterns.yaml` — regex deny-list for Indian PII (PAN, Aadhaar, email, phone, OTP).
- `config/disclaimer.txt` — `"Facts-only. No investment advice."`

### `config/sources.yaml` — final registry for this iteration

```yaml
schemes:
  - id: hdfc_mid_cap
    name: HDFC Mid Cap Fund - Direct Growth
    category: Mid Cap
    sources:
      - url: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
        doc_type: Product_Page

  - id: hdfc_equity
    name: HDFC Equity Fund - Direct Growth
    category: Flexi Cap
    sources:
      - url: https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
        doc_type: Product_Page

  - id: hdfc_focused
    name: HDFC Focused Fund - Direct Growth
    category: Focused
    sources:
      - url: https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
        doc_type: Product_Page

  - id: hdfc_elss
    name: HDFC ELSS Tax Saver - Direct Plan Growth
    category: ELSS
    sources:
      - url: https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
        doc_type: Product_Page

  - id: hdfc_large_cap
    name: HDFC Large Cap Fund - Direct Growth
    category: Large Cap
    sources:
      - url: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
        doc_type: Product_Page

# Hard rule: any URL not present in this file MUST NOT appear in any answer.
# CI compliance gate (Phase 5) fails the build if a generated answer cites a URL
# outside this list.
```

### Exit Criteria

- `sources.yaml` contains exactly 5 entries — the 5 Groww URLs above — and nothing else.
- A reviewer can diff the URL list against the problem statement and confirm 1:1 match.
- Refusal copy and "I don't know" copy never reference any URL outside the 5.

---

## Phase 1 — Ingestion & Corpus Build (Offline Pipeline)

**Purpose**: convert the 5 whitelisted Groww URLs into a clean, chunked, embedded, queryable corpus.

```
URLs ─► 1.1 Fetcher ─► 1.2 Extractor ─► 1.3 Cleaner ─► 1.4 Chunker ─► 1.5 Embedder ─► 1.6 Indexer
                                                                                          │
                                                                              1.7 Refresh & Health
                                                                              (orchestrates 1.1–1.6)
```

> **Scheduled refresh**: use a GitHub Actions workflow with `on: schedule:` (and optionally `workflow_dispatch` for manual runs). Each run executes the Phase 1 toolchain so the corpus and index stay aligned with live Groww pages without a dedicated VM cron.

Phase 1 is broken into 7 sub-phases, each independently demoable.

---

### Sub-phase 1.1 — Fetcher

**Purpose**: pull the 5 Groww HTML pages and persist raw snapshots.

- **Input**: `config/sources.yaml` (the 5 URLs from Phase 0).
- **Output**: `data/raw/<scheme_id>/<timestamp>.html` + a sibling `meta.json` per fetch (`{url, fetched_at, http_status, etag, content_hash_raw, fetcher_kind}`).
- **Module**: `src/mf_faq/ingestion/fetcher.py` → `Fetcher.fetch_all() -> list[FetchResult]`
- **Tech**: `httpx` for plain HTTP; if extracted text length / required-keyword presence is below threshold, fall back to headless `playwright`.

**Behavior**:
- Respect `robots.txt` before each scheduled run; abort whole run if disallowed.
- Send `If-None-Match` (ETag) on subsequent runs; on 304, skip and reuse the previous snapshot.
- On 4xx/429: stop, alert, retry next scheduled run — never bypass anti-bot.
- On 301/302 of a whitelisted URL: do not auto-follow; raise a governance alert.

**Edge cases addressed**: EC-1.1, EC-1.2, EC-1.3, EC-1.10.

**Exit criteria**: all 5 URLs fetched, each `data/raw/.../*.html` ≥ minimum byte size, `meta.json` present, fetcher run reports `health=ok` for all 5.

---

### Sub-phase 1.2 — Extractor

**Purpose**: HTML → structured text with section anchors (Overview, Scheme Details, Exit Load, Expense Ratio, Min SIP, Riskometer, Benchmark, FAQs).

- **Input**: raw HTML files from 1.1.
- **Output**: `data/processed/<scheme_id>/extracted.json`

```json
{
  "scheme_id": "hdfc_equity",
  "source_url": "https://groww.in/...",
  "fetched_at": "2026-05-03T10:00:00Z",
  "sections": [
    {"name": "Expense Ratio", "text": "..."},
    {"name": "Exit Load",     "text": "..."},
    {"name": "Scheme Details","text": "..."}
  ],
  "must_have_anchors": {"Expense Ratio": true, "Exit Load": true},
  "extraction_health": "ok"
}
```

- **Module**: `src/mf_faq/ingestion/extractor.py` → `Extractor.extract(html, scheme_id) -> ExtractedDoc`
- **Tech**: `trafilatura` for main-body text + targeted CSS/XPath selectors for each must-have anchor + `BeautifulSoup` for table cells (expense ratio, exit load).

**Behavior**:
- Maintain a per-page must-have anchors list; a missing anchor flips `extraction_health` to `degraded` and is logged.
- For image-only facts (riskometer SVG): read `alt` / `aria-label` / sibling caption; if all absent, mark `not-extracted` (no OCR).
- Run desktop viewport when JS rendering is needed; auto-expand `[aria-expanded="false"]` accordions.

**Edge cases addressed**: EC-1.4, EC-1.5, EC-1.7, EC-1.10.

**Exit criteria**: for all 5 schemes, extracted JSON exists; ≥ 4 of the must-have anchors present per page; `extraction_health=ok` on the golden snapshot.

---

### Sub-phase 1.3 — Cleaner & Normalizer

**Purpose**: strip boilerplate, normalize encoding so retrieval tokens match user queries.

- **Input**: extracted JSON from 1.2.
- **Output**: `data/processed/<scheme_id>/cleaned.json` — same shape as extracted, but each section's text is cleaned.
- **Module**: `src/mf_faq/ingestion/cleaner.py` → `Cleaner.clean(doc) -> ExtractedDoc`

**Behavior**:
- Drop known boilerplate (`"Mutual fund investments are subject to market risks…"`, `"You may also like"`, footer links).
- Unicode NFKC normalization; collapse whitespace; map `Rs.` / `INR` → `₹`; normalize `%`, `–`, `—`, smart quotes.
- Strip volatile fields from a stable view of the doc (NAV, `"as on "`, today's AUM) to feed the `stable_content_hash` (see 1.7).

**Section drop / trim policy**:
- **Drop entirely**: the FAQ section. The extractor still parses the FAQPage JSON-LD as a must-have-anchor health signal, but the Q&A content is not part of the facts-only corpus.
- **Trim aggressively**:
  - *Fund Manager*: keeps just the manager's name and tenure; bio (Education / Experience) is dropped.
  - *Fund House*: keeps AMC name, rank, total AUM, and incorporation date; phone / email / website / address are dropped.

**Edge cases addressed**: EC-1.6, EC-1.8, EC-1.12.

**Exit criteria**: cleaned text contains zero entries from the boilerplate strip-list; `cleaned.json` contains no FAQ section; `Rs.500` / `Rs. 500` / `₹500` all collapse to `₹500`.

---

### Sub-phase 1.4 — Chunker

**Purpose**: section-aware splitting into retrieval units, with full provenance metadata.

- **Input**: cleaned JSON from 1.3.
- **Output**: `data/processed/<scheme_id>/chunks.jsonl` — one JSON per line:

```json
{
  "chunk_id": "uuid",
  "scheme_id": "hdfc_equity",
  "scheme_name": "HDFC Equity Fund - Direct Growth",
  "doc_type": "Product_Page",
  "source_url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
  "section": "Exit Load and Tax",
  "section_source": "html_section",
  "last_updated": "2026-04-15",
  "content_hash": "sha256:...",
  "stable_content_hash": "sha256:...",
  "text": "..."
}
```

- **Module**: `src/mf_faq/ingestion/chunker.py` → `Chunker.chunk(doc) -> Iterable[Chunk]`

**Behavior**:
- **Section never spans chunks**. Each chunk's `section` is exactly one cleaned-doc section name — never a comma-joined list.
- **One section → one chunk by default**. All sections except *About* fall well under the soft cap (~250 tokens) and are emitted whole.
- **Soft cap = 250 tokens, hard cap = 400 tokens, overlap = 30 tokens** — only triggers for long sections (today: just *About*). Splits happen on sentence boundaries; never mid-sentence and never mid-numeric-fact (e.g., `"₹14,615.19 Cr"` must stay together).
- **No `scheme_name` prepend in chunk text** — the embedder (1.5) prepends it transiently before vectorization to avoid near-duplicate boilerplate clustering across schemes. Storing it in text would corrupt downstream display and BM25 tokenization.
- **Atomic table rows** — tabular text like Fund Details is treated as one unit even if layout grows.
- **Drop empty / tiny chunks** — if a section's text is < 5 tokens after cleaning, skip it.

**Expected output volume**: ~7 chunks per scheme → ~35 chunks total across the 5 schemes.

**Edge cases addressed**: EC-1.8, EC-1.9, EC-2.5.

**Exit criteria**:
- Each chunk's `section` is a single value drawn from the cleaned doc's section set.
- Every chunk's `source_url` ∈ the Phase 0 whitelist (string-equal match).
- Total chunk count is in the band `5 ≤ n ≤ 12` per scheme.
- Numeric facts (`₹X Cr`, `X.XX%`, `X year(s)`) are never split across chunks.

---

### Sub-phase 1.5 — Embedder

**Purpose**: generate dense vectors per chunk.

- **Input**: chunks from 1.4.
- **Output**: `data/index/embeddings.parquet` with rows `{chunk_id, embedding[float32]}` + sidecar `embedder.json: {"model": "bge-small-en", "version": "1.5", "dim": 384}`.
- **Module**: `src/mf_faq/ingestion/embedder.py` → `Embedder.embed(chunks) -> EmbeddingBatch`
- **Tech**: `bge-small-en` via `sentence-transformers`, OR `text-embedding-3-small` via the OpenAI API (configurable).

**Behavior**:
- Embed `f"{scheme_name}\n\n{text}"` so near-duplicate boilerplate across schemes still vectors-apart (EC-1.8).
- Persist the embedder model + version next to vectors; retriever (Phase 2) refuses to load mismatched versions.

**Edge cases addressed**: EC-1.8, EC-1.11.

**Exit criteria**: every chunk has exactly one embedding of expected dimension; `embedder.json` is present; reload round-trip preserves vectors bit-for-bit.

---

### Sub-phase 1.6 — Indexer

**Purpose**: build the dense + BM25 indexes that Phase 2 queries against. **This is the exact phase where generated embeddings are stored in the vector database (ChromaDB persistent store or FAISS vector index).**

- **Input**: chunks (1.4) + embeddings (1.5).
- **Output**: `data/index/`:
  - `vector.faiss` (or persistent Chroma DB files inside `data/index/`) — dense index keyed by `chunk_id`.
  - `bm25.pkl` — sparse index over chunk text.
  - `chunks.jsonl` — canonical chunk store (with metadata).
  - `manifest.json` — `{built_at, embedder, n_chunks, per_scheme_counts, source_hashes}`.
- **Module**: `src/mf_faq/ingestion/indexer.py` → `Indexer.build()`, `Indexer.load() -> IndexHandle` (Chroma DB operations are handled via `src/mf_faq/vector_db/chroma_store.py`)
- **Tech**: Chroma (via `chromadb` persistent client storage) or FAISS for dense; `rank_bm25` / Whoosh for sparse.

**Behavior**:
- **Atomic swap**: build into `data/index/.staging/`, then rename. Phase 2 readers see only fully-built indexes.
- Manifest doubles as the corpus passport — Phase 5 reads it for freshness reporting.

**Edge cases addressed**: EC-1.11.

**Exit criteria**: Phase 2 can open the index and run a sample query end-to-end; manifest's `n_chunks` matches the chunk store; per-scheme counts are non-zero for all 5.

---

### Sub-phase 1.7 — Refresh & Health

**Purpose**: orchestrate 1.1 → 1.6 as a re-runnable pipeline with drift detection and health reporting.

- **Input**: none directly — runs on a schedule.
- **Output**: `data/index/refresh_log.jsonl` — one line per run with per-stage timings, content-hash diffs, anchor health, and outcome ∈ `{ok, partial, frozen}`.
- **Module**: `src/mf_faq/ingestion/pipeline/service.py` → `Pipeline.refresh(force=False, dry_run=False, skip_fetch=False)`

**Scheduler (GitHub Actions)**:
- **Automation**: To keep the vector DB (ChromaDB) and indexes dynamically synchronized with live Groww page changes without a persistent VM, we run the entire Phase 1 pipeline on a scheduled **GitHub Actions workflow**.
- **Trigger**: Configured with `on: schedule:` cron syntax (e.g., nightly/weekly UTC cron) to pull fresh data, and supports manual runs via `workflow_dispatch`.
- **Secrets Management**: Sensitive credentials (such as `GROQ_API_KEY`) are stored in and fetched securely from GitHub Secrets.
- **Typical job steps**: checkout → install Python (e.g. 3.10+) → install dependencies (`pip install -r requirements.txt`) → execute ingestion pipeline (`python -m mf_faq.ingestion.pipeline.run`) → check drift & update indices safely → commit back to repo or archive artifacts.

**Behavior**:
- For each URL, compute `stable_content_hash` (volatile fields excluded); only re-chunk + re-embed pages whose stable hash changed.
- On drift across ≥ 2 URLs in the same window → freeze the index (don't overwrite), raise a single aggregated alert.
- Soft-404 detection (HTTP 200 but missing must-have anchors) → fail that URL, keep the rest.
- `"Last updated from sources"` date in chunk metadata is bumped only when stable content actually changed.

**Edge cases addressed**: EC-1.6, EC-1.10, EC-5.7, EC-5.8.

**Exit criteria**: dry-run on the bundled snapshot fixtures produces a deterministic `refresh_log.jsonl`; a synthetic drift across 3 URLs triggers the freeze path with one alert.

---

### Phase 1 Overall Exit Criteria

The index contains chunks from all 5 Groww URLs (~7 per page → ~35 total); every chunk's `source_url` ∈ the 5-URL whitelist; the manifest reports a fully-healthy build; Phase 2 can open and query the index.

---

## Phase 2 — Retrieval Layer

**Purpose**: given a user query, surface the minimum set of chunks needed to answer factually.

### Pipeline

```
Query
  │
  ├─► Query Normalizer  (NFKC, lowercase, collapse whitespace; MF tokens: ELSS/SIP/NAV/AUM)
  │
  ├─► Scheme Resolver   (NER-lite: longest substring match on scheme name + aliases from sources.yaml)
  │
  ├─► Hybrid Retriever
  │     ├─ Dense  (same HF model as Phase 1.5; query = normalized text)
  │     └─ Sparse (BM25, same tokenization as Phase 1.6 index)
  │     → Weighted Reciprocal Rank Fusion → fused top-10
  │       • Default equal weights; numeric-heavy queries (digits / ₹ / %) bump sparse weight vs dense.
  │       • Small corpus (~35 chunks): effective top_k per channel is min(20, n_candidates) after scheme filter.
  │
  ├─► Optional section hint — light score boost when query keywords match a chunk's section
  │   (e.g. "exit load" → Exit Load and Tax)
  │
  ├─► Cross-encoder Re-ranker  (default: BAAI/bge-reranker-base) → top-3 passages
  │
  └─► Confidence Gate   — low confidence when rerank margin (top − 2nd) is tiny → "I don't know" path
```

**Why hybrid + rerank?** Mutual fund queries mix exact tokens (e.g., `"0.45%"`, `"1 year"`, `"₹500"`) with semantic phrasing (`"how long is the lock-in?"`). BM25 nails exact, dense nails semantic; the cross-encoder picks the best chunk.

### Filters applied before retrieval

- `scheme_id = <resolved scheme>` → intersect hybrid candidate lists with chunks for that scheme only. If that filters out all candidates, relax the scheme filter once and search the full corpus.
- `doc_type = Product_Page` (only doc type in the corpus for this iteration).

**Implementation**: `mf_faq.retrieval` — `HybridRetriever` loads `IndexHandle` + `Embedder` (from `embedder.json`) + cross-encoder.

**Exit criteria**: top-1 chunk contains the gold answer for ≥ 85% of a 30-question eval set.

---

## Phase 3 — Reasoning & Guardrails (Orchestrator)

**Purpose**: turn a query + retrieved chunks into a compliant, ≤ 3-sentence answer — or a refusal — with URL policy enforced before anything is returned.

**Generation stack**: when an LLM is used, it is **Groq** via the OpenAI-compatible Chat Completions API (`pip install "mf-faq[groq]"`, env `GROQ_API_KEY`). Default: `use_groq=None` (auto) — Groq runs when `GROQ_API_KEY` is set; extractive-only otherwise.

### URL Policy (non-negotiable)

| Situation | URLs in the assistant reply |
|:--|:--|
| PII detected in the user message (PAN, Aadhaar, email, phone, OTP) | **None** — use the locked `pii_block` template only |
| Insufficient evidence / low confidence / empty retrieval | **None** — use `dont_know_without_link` only |
| Non-factual intent (advisory / comparison / prediction refusal) | **At most one** — the matching scheme's Groww URL from `sources.yaml` |
| Successful factual answer from retrieved chunks | **Exactly one** — the `source_url` from the top chunk (must be on the whitelist) |

### Decision Flow

```
              ┌──────────────────────────┐
              │   Incoming user query    │
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
      ┌──No──┤   PII detected?          │
      │      └────────────┬─────────────┘
      │                   │ Yes
      │                   ▼
      │      pii_block template — NO URL
      ▼
┌───────────────────────────────────────┐
│  Intent Classifier                    │
│  {factual | advisory | comparison |   │
│   prediction}                         │
└───────────┬─────────────┬─────────────┘
            │ factual     │ advisory / comparison / prediction
            ▼             ▼
  ┌─────────────────┐  ┌──────────────────────────────────┐
  │ Retriever       │  │ Refusal Composer                 │
  │ (Phase 2)       │  │ • polite; facts-only policy      │
  └────────┬────────┘  │ • exactly ONE Groww URL from     │
           ▼           │   whitelist (scheme match or     │
  ┌─────────────────┐  │   default first scheme)          │
  │ Confidence ≥ τ? │  └──────────────────────────────────┘
  │ & hits non-empty│
  └──┬───────────┬──┘
  No │           │ Yes
     ▼           ▼
dont_know      Groq or extractive body from top chunk
_without_link  (≤ 3 sentences) + Source: URL +
— NO URL       Last updated from sources: <date>
                │
                ▼
             Post-Processor
             • sentence count; banned tokens
             • exactly one whitelisted URL OR zero (see table above)
             • defensive PII scan on draft output
```

### Generator Contract

- **Extractive (default)**: build the body from the top reranked chunk only — first ≤ 3 sentences, strip any URLs embedded in chunk text so the reply does not accidentally contain extra links.
- **Groq (optional)**: `Orchestrator(..., use_groq=None)` (auto), or `use_groq=True` to force Groq, or `use_groq=False` for extractive-only. The model returns answer body only; `Source` and `Last updated` lines are appended in code. On API/import failure or empty body → extractive fallback.
- **Groq governance**: low temperature; same URL rules as extractive — no URL on PII block or don't-know; exactly one whitelisted URL on successful factual answers; refusals keep one educational URL.

### Hard Post-Checks (deterministic, non-LLM)

1. **Route-aware URL count**: PII and insufficient-evidence replies must contain zero `http(s)` URLs. Factual answers must contain exactly one URL, and it must appear in `sources.yaml`.
2. **Sentence count ≤ 3** for the factual body (before the `Source:` line).
3. **No banned tokens** in the full draft (e.g., `"recommend"`, `"should invest"`, `"better than"`, `"will outperform"`).
4. **Footer present** on successful factual path: `Last updated from sources: <YYYY-MM-DD>`.
5. If post-checks fail on an otherwise retrieved answer → fall back to safe template with one whitelisted link (`safe_template`).

**Exit criteria**: 100% of generated answers respect the URL policy above on the eval set; 0 hallucinated or extra URLs on factual paths.

---

## Phase 4 — User Interface (Minimal Web App)

**Purpose**: give a clean, trustworthy surface to the assistant.

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Mutual Fund FAQ Assistant                                   │
│  Facts-only. No investment advice.            [disclaimer]   │
├──────────────────────────────────────────────────────────────┤
│  Welcome! Ask a factual question about HDFC schemes.         │
│                                                              │
│  Try one of these:                                           │
│   • What is the expense ratio of HDFC Equity Fund?           │
│   • What is the exit load of HDFC Mid Cap Fund?              │
│   • What is the lock-in period for an ELSS fund?             │
├──────────────────────────────────────────────────────────────┤
│  [  type your question…                                ] [→] │
├──────────────────────────────────────────────────────────────┤
│  Answer area                                                 │
│  ─ short answer (≤3 sentences)                               │
│  ─ Source: <single link>                                     │
│  ─ Last updated from sources: <date>                         │
└──────────────────────────────────────────────────────────────┘
```

**Stack**: FastAPI in `mf_faq.ui` exposes `POST /ask`, `GET /meta`, `GET /health`, and serves a minimal static SPA from `mf_faq/ui/static/` at `/`. No login, no cookies beyond session, no analytics that capture query text with PII.

### UI Rules

- Disclaimer always visible.
- Submit button disabled while a query is in flight.
- Answer area renders the citation as a clickable link with `rel="noopener nofollow"`.
- "Copy answer" optional; "Share" deliberately omitted to discourage misuse.

**Exit criteria**: end-to-end demo: type question → get compliant answer with link + date.

---

## Phase 5 — Evaluation, Compliance & Observability

**Purpose**: prove the system is accurate, safe, and stays that way.

### 5a. Evaluation Harness

| Suite | What it checks | Pass bar |
|:--|:--|:--|
| Factual Q&A (30+ Qs) | Exact-match / numeric tolerance vs gold answer | ≥ 90% |
| Citation correctness | Cited URL actually contains the fact | 100% |
| Refusal suite (15+ Qs) | Advice/comparison/prediction queries get refused with educational link | 100% |
| Out-of-corpus | Query about unknown scheme → "I don't have a verified answer" | 100% |
| PII probes | Inputs with PAN/Aadhaar/email are rejected/redacted | 100% |
| Length & format | ≤ 3 sentences, 1 citation, footer present | 100% |

Tooling: a YAML test set + a small `pytest` runner that calls the API and asserts.

### 5b. Compliance Checks (CI Gate)

- Every URL in any answer ∈ `sources.yaml`.
- No banned advisory tokens in any answer.
- No PII tokens stored in logs (log-line scanner).

### 5c. Observability

- **Structured logs**: `{request_id, intent, retrieved_chunk_ids, confidence, post_check_passed, latency_ms}`.
- No raw queries with PII persisted; queries are hashed for analytics.
- **Dashboard (lightweight)**: refusal rate, "I don't know" rate, top schemes asked about, ingestion freshness.

### 5d. Operational Runbook

- Source change detection → alert when any of the 5 Groww URLs 404s or content hash drifts > X%.
- Weekly re-index job; manual override flag per source.

**Exit criteria**: all eval suites green in CI; runbook published.

---

## 3. Component Inventory (Cross-Phase)

| Layer | Component | Responsibility | Phase |
|:--|:--|:--|:--|
| Governance | `sources.yaml` | Whitelist of allowed URLs | 0 |
| Governance | `refusal_intents.yaml` | Refusal patterns + canned copy | 0 |
| Ingestion | Fetcher | HTTP download, ETag/hash tracking | 1 |
| Ingestion | Extractor + Cleaner | HTML → clean text, table-aware | 1 |
| Ingestion | Chunker | Heading-aware semantic chunking | 1 |
| Ingestion | Embedder | Vector generation | 1 |
| Storage | Vector store | Dense ANN search (FAISS/Chroma) | 1–2 |
| Storage | Keyword index | BM25 | 1–2 |
| Storage | Metadata store | Chunk metadata, source registry | 1–2 |
| Retrieval | Query normalizer | Acronym expansion, lowercase | 2 |
| Retrieval | Scheme resolver | Detect scheme to filter metadata | 2 |
| Retrieval | Hybrid retriever | Dense + BM25 + RRF | 2 |
| Retrieval | Re-ranker | Cross-encoder for precision | 2 |
| Orchestrator | PII guard | Reject inputs containing PII | 3 |
| Orchestrator | Intent classifier | factual vs advisory vs comparison | 3 |
| Orchestrator | Confidence gate | Trigger "I don't know" on low retrieval score | 3 |
| Generation | Groq LLM caller | Templated, low-temp chat completion (optional) | 3 |
| Generation | Post-processor | Length, citation, banned-token, PII checks | 3 |
| Generation | Refusal composer | Polite refusal + educational link | 3 |
| UI | FastAPI `/ask` API | JSON query → orchestrator result + structured logs | 4 |
| UI | Static SPA + CSS/JS | Welcome, examples, disclaimer, answer view | 4 |
| Quality | Eval harness | Factual + refusal + format + PII suites | 5 |
| Quality | Compliance CI gate | Whitelist + banned-token + PII log scan | 5 |
| Ops | Refresh scheduler | GitHub Actions schedule (cron) + `workflow_dispatch` | 1, 5 |
| Ops | Observability | Structured, PII-free logs + dashboard | 5 |

---

## 4. Data Flow — Single Query End-to-End

```
1.  User types: "What is the exit load of HDFC Equity Fund Direct Growth?"
2.  UI → POST /ask {query}
3.  PII guard           → clean
4.  Intent classifier   → factual
5.  Query normalizer    → "what is the exit load of hdfc equity fund direct growth"
6.  Scheme resolver     → scheme_id = hdfc_equity
7.  Hybrid retriever    → top-10 chunks from
                          https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
8.  Re-ranker           → top-1 chunk: "Scheme Details / Exit Load" section
9.  Confidence gate     → score 0.82 ≥ τ → proceed
10. Groq generator (or extractive) → ≤3 sentence answer using only that chunk
11. Post-processor     → length OK, 1 URL OK, URL ∈ 5-URL whitelist OK,
                         no banned tokens, footer appended
12. Response:
    "HDFC Equity Fund Direct Growth charges an exit load of 1% if units are
     redeemed within 1 year of allotment; no exit load applies thereafter.
     Source: https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
     Last updated from sources: 2026-04-15"
13. Logs: {request_id, intent=factual, scheme_id=hdfc_equity,
           chunk_ids=[...], conf=0.82, checks=passed, latency_ms=740}
           (no raw query stored)
```

---

## 5. Risks & Mitigations

| Risk | Mitigation |
|:--|:--|
| Groww updates a page → stale answer | Content-hash diff in nightly job; bump `last_updated`; alert if drift big |
| Groq model hallucinates a number | Numeric values must appear verbatim in retrieved chunk (regex check) |
| Groq model emits a non-whitelisted URL | Post-processor rejects + falls back to safe template |
| User asks for advice | Intent classifier + refusal composer (link = matching Groww scheme URL) |
| User pastes PAN/Aadhaar/email/phone | PII guard rejects request before retrieval; never logged |
| Ambiguous scheme name | Scheme resolver asks clarifying question (still facts-only, no opinions) |
| Performance/return question | Redirect to the relevant Groww scheme URL; never compute or compare returns |
| Low-confidence retrieval | "I don't have a verified answer" + matching Groww scheme URL |
| Fact only present in KIM/SID (off-corpus) | Return "I don't have a verified answer" + matching Groww scheme URL |

---

## 6. Phase Roadmap (Suggested Timeline)

| Phase | Outcome | Indicative effort |
|:--|:--|:--|
| 0 | Sources whitelisted, refusal taxonomy ready | 0.5 day |
| 1 | Corpus ingested + indexed | 1.5 days |
| 2 | Hybrid retrieval + reranker working | 1 day |
| 3 | Orchestrator + guardrails + generator | 1.5 days |
| 4 | Minimal UI wired end-to-end | 0.5 day |
| 5 | Eval suites + CI gates + observability | 1 day |

---

## 7. Alignment to Problem Statement

| Requirement | Where addressed / iteration scope |
|:--|:--|
| Curated corpus | Phase 0 — corpus is exactly the 5 Groww HDFC scheme URLs (locked in `sources.yaml`) |
| 3–5 schemes, category diversity | Phase 0 — 5 schemes: Mid Cap, Flexi Cap, Focused, ELSS, Large Cap |
| ≤ 3 sentences, exactly 1 citation | Phase 3 (prompt contract + deterministic post-checks) |
| Footer `"Last updated from sources: "` | Phase 3 (post-processor) |
| Refuse advisory queries with educational link | Phase 3 — link returned is the matching Groww scheme URL (one of the 5) |
| Welcome msg, 3 examples, visible disclaimer | Phase 4 (UI) |
| No PII collection/storage | Phase 3 (PII guard) + Phase 5 (log scanner) |
| Source restriction | Phase 0 — `sources.yaml` contains only the 5 Groww URLs; Phase 5 CI fails on any other URL in output |
| Performance queries | Phase 3 — redirect to the relevant Groww scheme URL; no returns computation/comparison |
| Accuracy + auditability | Phase 5 (eval suites + structured PII-free logs) |
| Statement / capital-gains / KIM-only facts | Out of scope this iteration — assistant returns "I don't have a verified answer" + Groww URL |

---

## Disclaimer Snippet

> **Facts-only. No investment advice.**
