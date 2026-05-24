# Mutual Fund FAQ Assistant - Phase-wise Architecture

## Executive Summary

This document outlines the detailed phase-wise architecture for building a facts-only FAQ assistant for mutual fund schemes. The system is designed as a Retrieval-Augmented Generation (RAG)-based assistant that answers objective, verifiable queries exclusively from official sources while strictly avoiding investment advice or recommendations.

**Project Duration:** 6 days total  
**Target AMC:** HDFC Mutual Fund  
**Corpus Scope:** 5 Groww HDFC scheme URLs (strictly limited)  
**Core Principle:** Facts-over-Intelligence with auditability and compliance

---

## Architectural Principles

1. **Facts-over-Intelligence** - Retrieval grounds every answer; LLM only reformats retrieved facts
2. **Single Source of Truth** - Exactly one citation URL per response
3. **Closed Corpus** - Only whitelisted official URLs are ingested
4. **Refusal by Default** - Advisory/opinion queries are deflected with educational redirects
5. **PII-Free** - No personal data collection, logging, or processing
6. **Determinism > Creativity** - Low temperature, strict prompts, hard answer caps (≤3 sentences)
7. **Auditability** - Every response traceable to chunk, document, URL, and timestamp

---

## Phase 0 - Foundation & Governance
**Duration:** 0.5 day  
**Purpose:** Lock down scope, sources, and guardrails before code development

### 🔒 Locked Corpus — Exactly These 5 URLs, Nothing Else

> **⚠️ HARD CONSTRAINT — FOR THIS PROJECT:**  
> We will use **ONLY** the following 5 URLs, exactly as written. No other URLs are to be ingested, processed, fetched, embedded, indexed, or cited — under any circumstance.  
> - ❌ No AMC PDFs (KIM / SID / factsheets)  
> - ❌ No AMFI pages  
> - ❌ No SEBI pages  
> - ❌ No AMC website FAQ pages  
> - ❌ No other Groww pages beyond these 5  
>
> Every fact the assistant returns must trace back to exactly one of these 5 URLs.  
> Every citation must be one of these 5 URLs — verbatim, string-equal.

```
https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
```

### Selected Corpus

| # | Scheme | Category | Source URL |
|:--|:--|:--|:--|
| 1 | HDFC Mid Cap Fund - Direct Growth | Mid Cap | `https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth` |
| 2 | HDFC Equity Fund - Direct Growth | Flexi Cap | `https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth` |
| 3 | HDFC Focused Fund - Direct Growth | Focused | `https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth` |
| 4 | HDFC ELSS Tax Saver - Direct Plan Growth | ELSS | `https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth` |
| 5 | HDFC Large Cap Fund - Direct Growth | Large Cap | `https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth` |

### Deliverables
- `config/sources.yaml` — Registry of **exactly these 5 whitelisted URLs** (no more, no less)
- `config/refusal_intents.yaml` — Refusal patterns and canned responses (educational links always from these 5 URLs)
- `config/disclaimer.txt` — "Facts-only. No investment advice."
- PII deny-list and redaction regex patterns
- Governance rules for URL citation enforcement

### Exit Criteria
- `sources.yaml` contains **exactly 5 entries** — the 5 Groww URLs above — and nothing else
- A reviewer can diff the URL list against the problem statement and confirm 1:1 match
- Refusal copy and "I don't know" copy never reference any URL outside these 5
- All governance rules documented and reviewable

---

## Phase 1 - Ingestion & Corpus Build
**Duration:** 1.5 days  
**Purpose:** Convert 5 whitelisted URLs into clean, chunked, embedded, queryable corpus

**Target URLs (Exclusive Corpus):**
- https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
- https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
- https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
- https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
- https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth

**Important:** For this project, we will use ONLY these 5 URLs exactly as listed above. No other URLs will be ingested, processed, or cited in any responses.

### Architecture Flow
```
URLs → 1.1 Fetcher → 1.2 Extractor → 1.3 Cleaner → 1.4 Chunker → 1.5 Embedder → 1.6 Indexer
                                                                  │
                                                          1.7 Refresh & Health (Orchestrator)
```

### Sub-phase 1.1 - Fetcher
**Module:** `src/mf_faq/ingestion/fetcher.py`  
**Tech Stack:** httpx + Playwright (fallback)

**Responsibilities:**
- Pull 5 Groww HTML pages with ETag support
- Respect robots.txt compliance
- Handle 4xx/429 with retry logic
- Detect and alert on redirects (301/302)
- Persist raw snapshots with metadata

**Outputs:**
```
data/raw/<scheme_id>/<timestamp>.html
data/raw/<scheme_id>/<timestamp>.meta.json
```

**Exit Criteria:** All URLs fetched successfully with metadata intact

### Sub-phase 1.2 - Extractor
**Module:** `src/mf_faq/ingestion/extractor.py`  
**Tech Stack:** trafilatura + BeautifulSoup + CSS/XPath selectors

**Responsibilities:**
- HTML → structured text with section anchors
- Extract must-have sections: Expense Ratio, Exit Load, Scheme Details, etc.
- Handle JS-rendered content and accordions
- Process image-based content (riskometer) via alt/aria-label

**Output:**
```json
{
  "scheme_id": "hdfc_equity",
  "source_url": "https://groww.in/...",
  "fetched_at": "2026-05-03T10:00:00Z",
  "sections": [
    {"name": "Expense Ratio", "text": "..."},
    {"name": "Exit Load", "text": "..."}
  ],
  "must_have_anchors": {"Expense Ratio": true, "Exit Load": true},
  "extraction_health": "ok"
}
```

**Exit Criteria:** ≥4 must-have anchors present per page

### Sub-phase 1.3 - Cleaner & Normalizer
**Module:** `src/mf_faq/ingestion/cleaner.py`

**Responsibilities:**
- Strip boilerplate content ("market risks", "You may also like")
- Unicode NFKC normalization
- Currency symbol standardization (Rs./INR → ₹)
- Remove volatile fields (NAV, current AUM) for stable hashing
- Section policy: Drop FAQ entirely, trim Fund Manager bios

**Exit Criteria:** Zero boilerplate entries, no FAQ section, normalized currency

### Sub-phase 1.4 - Chunker
**Module:** `src/mf_faq/ingestion/chunker.py`

**Chunking Strategy:**
- Filter empty sections first (FAQ dropped, volatile fields removed)
- One section → one chunk (default), with length-based splitting
- Soft cap: 250 tokens, Hard cap: 400 tokens
- Sentence boundary splitting (never mid-fact)
- Preserve atomic table rows from financial data
- Merge sections under 50 tokens with related content
- Expected output: 5-7 chunks per scheme → 25-35 total

**Actual Cleaned Data Structure:**
Based on Phase 1.3 cleaner output, realistic sections after processing:
- Expense Ratio (1-2 chunks) - Financial data with tables
- Exit Load (1 chunk) - Short, factual statements
- Scheme Details (1-2 chunks) - May include tabular data
- Minimum Investments (1 chunk) - SIP/Lumpsum amounts
- Fund Manager (1 chunk) - Name + tenure only (very short)
- Fund House (1 chunk) - AMC name + basic info
- Riskometer (1 chunk) - Risk level description
- Benchmark (1 chunk) - Benchmark index info
- About (1-2 chunks) - Longer descriptive content
- FAQ sections: **DROPPED ENTIRELY**

**Special Handling Rules:**
- Empty sections: Skip entirely (no chunks created)
- Short sections (<50 tokens): Consider merging with related sections
- Table content: Preserve row structure, split at table boundaries
- Financial data: Never split numeric facts across chunks

**Output Format:**
```json
{
  "chunk_id": "uuid",
  "scheme_id": "hdfc_equity",
  "scheme_name": "HDFC Equity Fund - Direct Growth",
  "source_url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
  "section": "Exit Load",
  "last_updated": "2026-05-12T00:00:00Z",
  "content_hash": "sha256:...",
  "stable_content_hash": "sha256:...",
  "text": "Exit load: 0% if redeemed after 1 year, 1% before 1 year",
  "token_count": 45,
  "chunk_order": 3
}
```

**Exit Criteria:** 
- All chunks have valid whitelisted URLs from sources.yaml
- No split numeric facts across chunk boundaries
- Empty sections (FAQ, removed content) are properly excluded
- Token counts respect soft/hard caps (50-400 tokens)
- Stable content hash matches cleaner output
- Short sections (<50 tokens) handled appropriately (merged or standalone)
- Table row structure preserved in financial sections

### Sub-phase 1.5 - Embedder
**Module:** `src/mf_faq/ingestion/embedder.py`  
**Tech Stack:** sentence-transformers (bge-small-en) or OpenAI embeddings

**Strategy:**
- Embed `f"{scheme_name}\n\n{text}"` to avoid boilerplate clustering
- Persist model metadata alongside vectors
- 384-dimensional vectors for bge-small-en

**Outputs:**
- `data/index/embeddings.parquet`
- `embedder.json` (model metadata)

**Exit Criteria:** All chunks have embeddings, model version tracked

### Sub-phase 1.6 - Indexer
**Module:** `src/mf_faq/ingestion/indexer.py` (Chroma DB operations are handled via `src/mf_faq/vector_db/chroma_store.py`)  
**Tech Stack:** ChromaDB (persistent vector database) / FAISS (dense) + rank_bm25 (sparse)

**Responsibilities:**
- **Store generated embeddings** inside the persistent vector database (ChromaDB collection or FAISS vector index)
- Build dense and sparse indexes
- Atomic swap (staging → production)
- Generate manifest with corpus metadata

**Outputs:**
```
data/index/vector.faiss (or persistent Chroma DB files inside data/index/)
data/index/bm25.pkl
data/index/chunks.jsonl
data/index/manifest.json
```

**Exit Criteria:** Phase 2 can query the vector database and indexes successfully

### Sub-phase 1.7 - Refresh & Health
**Module:** `src/mf_faq/ingestion/pipeline/service.py`  
**Scheduler:** GitHub Actions (nightly/weekly)

**Responsibilities:**
- Orchestrate 1.1 → 1.6 pipeline
- Content hash diff detection
- Drift alerts (≥2 URLs changed simultaneously)
- Soft-404 detection
- Stable content hash for incremental updates
- Automated architecture document updates on pipeline changes

#### GitHub Actions Ingestion Scheduler
To keep the retrieval index dynamically synchronized with the latest Groww data without hosting a persistent cron daemon, a scheduled **GitHub Actions workflow** is configured.

**Workflow Configuration (`.github/workflows/ingestion_scheduler.yml`):**
- **Trigger**: Run automatically on a recurring cron schedule (e.g., nightly at 00:00 UTC) and support manual triggers via `workflow_dispatch`.
- **Secrets Management**: Retrieve API credentials (like `GROQ_API_KEY`) securely via GitHub Secrets.
- **Workflow Pipeline Steps**:
  1. **Checkout Code**: Checkout the current repository branch.
  2. **Set up Environment**: Install Python (e.g., 3.10+) and standard system packages.
  3. **Install Dependencies**: Execute `pip install -r requirements.txt` to install HTTP and processing toolchains.
  4. **Execute Ingestion**: Run the orchestrator pipeline command (e.g. `python -m mf_faq.ingestion.pipeline.run`) to fetch, parse, clean, chunk, embed, and re-index the 5 HDFC schemes.
  5. **Drift and Freeze Checks**: If content drift is within limits, commit and push updated indices (`data/index/`) to the repository branch, or archive them as workflow build artifacts. If severe drift is detected, lock/freeze the indexing process to prevent corrupting production data and trigger alert logs.

**Exit Criteria:** Deterministic refresh behavior, proper freeze on drift, and successful automated indexing run on dispatch.

---

## Phase 2 - Retrieval Layer
**Duration:** 1 day  
**Purpose:** Surface minimum set of chunks needed for factual answers

### Pipeline Architecture
```
Query → Query Normalizer → Scheme Resolver → Hybrid Retriever → Cross-encoder Re-ranker → Confidence Gate
```

### Components

#### Query Normalizer
- NFKC normalization, lowercase, whitespace collapse

#### Scheme Resolver
- Pre-filter chunks by scheme relevance based on query terms
- Boost scheme-specific results in fusion

#### Hybrid Retriever
- Weighted Reciprocal Rank Fusion (WRRF)
- Default equal weights, sparse boost for numeric queries
- Top-k: min(20, n_candidates) after scheme filtering

#### Cross-encoder Re-ranker
- Model: BAAI/bge-reranker-base
- Purpose: Precision improvement on fused candidates
- Output: Top-3 passages for confidence scoring

#### Confidence Gate
- Threshold-based filtering
- Low margin (top - 2nd) triggers "I don't know" path
- Configurable confidence threshold τ

### Implementation
**Module:** `mf_faq.retrieval.HybridRetriever`  
**CLI:** `python -m mf_faq.retrieval "your question"`

### Exit Criteria
- Top-1 chunk contains gold answer for ≥85% of 30-question eval set
- Sub-second response times for typical queries
- MF token expansion (ELSS/SIP/NAV/AUM)

#### Scheme Resolver
- NER-lite for scheme name detection
- Longest substring matching against sources.yaml
- Alias support for common abbreviations

#### Hybrid Retriever
**Dense Retrieval:**
- Same model as Phase 1.5 for consistency
- Query format: `scheme_name\n\n{normalized_query}` when scheme detected

**Sparse Retrieval:**
- BM25 with same tokenization as index
- Boost for numeric-heavy queries (₹, %, digits)

**Fusion:**
- Weighted Reciprocal Rank Fusion (WRRF)
- Default equal weights, sparse boost for numeric queries
- Top-k: min(20, n_candidates) after scheme filtering

#### Cross-encoder Re-ranker
**Model:** BAAI/bge-reranker-base  
**Purpose:** Precision improvement on fused candidates  
**Output:** Top-3 passages for confidence scoring

#### Confidence Gate
- Threshold-based filtering
- Low margin (top - 2nd) triggers "I don't know" path
- Configurable confidence threshold τ

### Implementation
**Module:** `mf_faq.retrieval.HybridRetriever`  
**CLI:** `python -m mf_faq.retrieval "your question"`

### Exit Criteria
- Top-1 chunk contains gold answer for ≥85% of 30-question eval set
- Sub-second response times for typical queries

---

## Phase 3 - Reasoning & Guardrails
**Duration:** 1.5 days  
**Purpose:** Transform query + chunks into compliant answers with strict URL policy

### Decision Flow
```
User Query → PII Guard → Intent Classifier → [Factual|Advisory Paths] → Generator → Post-Processor
```

### Core Components

#### PII Guard
**Detection:** PAN, Aadhaar, email, phone, OTP patterns  
**Action:** Immediate rejection with template response  
**Policy:** Zero URLs in PII block responses

#### Intent Classifier
**Categories:** factual, advisory, comparison, prediction  
**Implementation:** Rule-based + lightweight ML  
**Routing:** Factual → Retrieval, Others → Refusal Composer

#### Confidence Gate
- Integrates with Phase 2 confidence scores
- Low confidence → "I don't have verified answer" path
- High confidence → Generation path

#### Generator Stack
**Options:**
1. **Extractive (Default):** Direct chunk synthesis
2. **Groq LLM (Optional):** Low-temp chat completion

**Groq Configuration:**
- Model: Groq-hosted via OpenAI-compatible API
- Temperature: Low (deterministic)
- Fallback: Extractive on API failure

#### Post-Processor
**Validations:**
- Sentence count ≤3 (before Source line)
- Exactly one whitelisted URL OR zero (PII/don't know)
- No banned tokens ("recommend", "should invest", etc.)
- Footer presence: "Last updated from sources: YYYY-MM-DD"
- Defensive PII scan on generated output

### URL Policy Enforcement Matrix
| Situation | URLs Allowed | Template |
|-----------|--------------|----------|
| PII detected | **Exactly 0** | `pii_block` (no URL - strictly 0 URLs to prevent any link exposure for sensitive/personal context) |
| Insufficient evidence | **Exactly 0** | `dont_know_without_link` (no URL - strictly 0 URLs to ensure ungrounded queries do not point to any resource) |
| Advisory/comparison/prediction | **Exactly 1** | `refusal` (matching scheme URL) |
| Successful factual answer | **Exactly 1** | `answer` (source URL from chunk) |

### Implementation
**Module:** `src/mf_faq/orchestrator/service.py`  
**Configuration:** `use_groq=None` (auto-detect based on API key)

### Exit Criteria
- 100% URL policy compliance on eval set
- Zero hallucinated URLs in factual responses
- All responses ≤3 sentences with proper citations

---

## Phase 4 - User Interface
**Duration:** 0.5 day  
**Purpose:** Clean, trustworthy web interface for the assistant

### UI Layout
```
┌──────────────────────────────────────────────────────────────┐
│  Mutual Fund FAQ Assistant                                   │
│  Facts-only. No investment advice.            [disclaimer]   │
├──────────────────────────────────────────────────────────────┤
│  Welcome! Ask a factual question about HDFC schemes.        │
│                                                              │
│  Try one of these:                                           │
│   • What is the expense ratio of HDFC Equity Fund?          │
│   • What is the exit load of HDFC Mid Cap Fund?             │
│   • What is the lock-in period for ELSS fund?               │
├──────────────────────────────────────────────────────────────┤
│  [  type your question…                                ] [→] │
├──────────────────────────────────────────────────────────────┤
│  Answer area                                                 │
│  ─ short answer (≤3 sentences)                               │
│  ─ Source: <single clickable link>                           │
│  ─ Last updated from sources: <date>                         │
└──────────────────────────────────────────────────────────────┘
```

### Technology Stack
**Backend:** FastAPI  
**Frontend:** Static SPA + CSS/JS  
**API Endpoints:**
- `POST /ask` - Query processing
- `GET /meta` - System metadata
- `GET /health` - Health check

### UI Rules
- Disclaimer always visible
- Submit button disabled during processing
- Citations as clickable links with `rel="noopener nofollow"`
- Optional "Copy answer" functionality
- No "Share" feature (prevent misuse)

### Privacy & Security
- No login required
- No persistent cookies beyond session
- No analytics that capture PII
- Same-origin fetch only

### Exit Criteria
- End-to-end demo: question → compliant answer with link + date
- Responsive design for mobile/desktop
- Accessibility compliance (WCAG 2.1 AA)

---

## Phase 5 - Evaluation, Compliance & Observability
**Duration:** 1 day  
**Purpose:** Prove system accuracy, safety, and ongoing reliability

### 5a. Evaluation Harness

#### Test Suites
| Suite | Questions | Pass Criteria |
|-------|-----------|---------------|
| Factual Q&A | 30+ | ≥90% exact/numeric tolerance |
| Citation Correctness | 30+ | 100% URL contains fact |
| Refusal Suite | 15+ | 100% proper refusal with educational link |
| Out-of-corpus | 10+ | 100% "I don't have verified answer" |
| PII Probes | 10+ | 100% rejection/redaction |
| Length & Format | 30+ | 100% ≤3 sentences, 1 citation, footer |

#### Implementation
**Format:** YAML test definitions + pytest runner  
**Execution:** Automated CI/CD pipeline  
**Reporting:** Detailed results with failure analysis

### 5b. Compliance Checks (CI Gate)

#### Automated Validations
- URL whitelist enforcement (all answers ∈ sources.yaml)
- Banned advisory token detection
- PII token scanning in logs
- Source hash integrity verification

#### Failure Modes
- Build failure on compliance violations
- Detailed violation reporting
- Manual review required for exceptions

### 5c. Observability

#### Structured Logging
```json
{
  "request_id": "uuid",
  "intent": "factual|advisory|comparison|prediction",
  "retrieved_chunk_ids": ["uuid1", "uuid2"],
  "confidence": 0.82,
  "post_check_passed": true,
  "latency_ms": 740,
  "scheme_id": "hdfc_equity"
}
```

#### Privacy-Preserving Analytics
- Query hashing for trend analysis
- No raw query storage with PII
- Aggregated metrics only

#### Dashboard Metrics
- Refusal rate by intent type
- "I don't know" rate
- Top schemes queried
- Ingestion freshness status
- Response latency distribution

### 5d. Operational Runbook

#### Monitoring
- Source URL availability (404 detection)
- Content hash drift alerts (>X% change)
- Index health and freshness
- API error rates and latency

#### Maintenance Procedures
- Manual refresh triggers
- Source URL updates (governance process)
- Model version updates
- Compliance rule updates

### Exit Criteria
- All eval suites passing in CI
- Compliance gates active and enforced
- Observability dashboard operational
- Runbook documented and tested

---

## Cross-Phase Component Inventory

| Layer | Component | Responsibility | Phase |
|-------|-----------|----------------|-------|
| Governance | sources.yaml | URL whitelist | 0 |
| Governance | refusal_intents.yaml | Refusal patterns | 0 |
| Ingestion | Fetcher | HTTP/PDF download | 1 |
| Ingestion | Extractor + Cleaner | HTML → clean text | 1 |
| Ingestion | Chunker | Semantic chunking | 1 |
| Ingestion | Embedder | Vector generation | 1 |
| Storage | Vector store | Dense ANN search | 1-2 |
| Storage | Keyword index | BM25 sparse search | 1-2 |
| Storage | Metadata store | Chunk metadata | 1-2 |
| Retrieval | Query normalizer | Text preprocessing | 2 |
| Retrieval | Scheme resolver | Scheme detection | 2 |
| Retrieval | Hybrid retriever | Dense + sparse fusion | 2 |
| Retrieval | Re-ranker | Cross-encoder ranking | 2 |
| Orchestrator | PII guard | PII detection/rejection | 3 |
| Orchestrator | Intent classifier | Intent categorization | 3 |
| Orchestrator | Confidence gate | Threshold filtering | 3 |
| Generation | Groq LLM caller | Optional generation | 3 |
| Generation | Post-processor | Output validation | 3 |
| Generation | Refusal composer | Polite refusals | 3 |
| UI | FastAPI /ask API | JSON query handling | 4 |
| UI | Static SPA + CSS/JS | User interface | 4 |
| Quality | Eval harness | Automated testing | 5 |
| Quality | Compliance CI gate | Policy enforcement | 5 |
| Ops | Refresh scheduler | Automated updates | 1,5 |
| Ops | Observability | Monitoring + logging | 5 |

---

## Data Flow - End-to-End Example

**Query:** "What is the exit load of HDFC Equity Fund Direct Growth?"

1. **UI Request:** POST /ask {query}
2. **PII Guard:** Clean (no PII detected)
3. **Intent Classifier:** factual
4. **Query Normalizer:** "what is the exit load of hdfc equity fund direct growth"
5. **Scheme Resolver:** scheme_id = hdfc_equity
6. **Hybrid Retrieval:** Top-10 chunks from HDFC Equity Fund URL
7. **Re-ranker:** Top-1 chunk from "Exit Load and Tax" section
8. **Confidence Gate:** Score 0.82 ≥ τ → proceed
9. **Generator:** "HDFC Equity Fund Direct Growth charges an exit load of 1% if units are redeemed within 1 year of allotment; no exit load applies thereafter."
10. **Post-Processor:** Length OK, 1 URL OK, no banned tokens, footer appended
11. **Final Response:**
    ```
    HDFC Equity Fund Direct Growth charges an exit load of 1% if units are
    redeemed within 1 year of allotment; no exit load applies thereafter.
    Source: https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
    Last updated from sources: 2026-04-15
    ```
12. **Logging:** {request_id, intent=factual, scheme_id=hdfc_equity, chunk_ids=[...], conf=0.82, checks=passed, latency_ms=740}

---

## Risk Management & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Groww page updates → stale answers | High | Content-hash diff detection, automated refresh, "last updated" timestamps |
| Groq model hallucination | Medium | Verbatim fact requirement, regex numeric validation, extractive fallback |
| Non-whitelisted URL generation | High | Post-processor URL whitelist enforcement, safe template fallback |
| Advisory query leakage | Medium | Intent classifier, refusal composer, educational redirects |
| PII exposure | High | Pre-processing PII guard, log scanning, no PII storage |
| Low-confidence retrieval | Medium | Confidence thresholds, "I don't know" responses |
| Scheme name ambiguity | Low | Scheme resolver with alias support, clarifying questions |
| Performance queries | Medium | Redirect to official factsheets, no return calculations |
| Off-corpus facts | Low | "I don't have verified answer" with relevant Groww link |

---

## Technology Stack Summary

### Core Technologies
- **Python 3.9+** - Primary development language
- **FastAPI** - Web framework and API server
- **FAISS** - Vector similarity search
- **sentence-transformers** - Text embeddings
- **BeautifulSoup4** - HTML parsing
- **trafilatura** - Content extraction
- **httpx** - HTTP client
- **Playwright** - Headless browser (fallback)

### Optional Components
- **Groq** - LLM generation (optional)
- **OpenAI** - Alternative embeddings
- **Chroma** - Alternative vector store

### Infrastructure
- **GitHub Actions** - CI/CD and scheduled refresh
- **pytest** - Testing framework
- **YAML** - Configuration management
- **JSON Lines** - Data storage format

---

## Success Metrics

### Technical Metrics
- **Accuracy:** ≥90% on factual Q&A eval set
- **Compliance:** 100% URL whitelist adherence
- **Latency:** <1 second average response time
- **Availability:** >99% uptime
- **Freshness:** <24 hour data staleness

### Business Metrics
- **User Trust:** Zero advisory content leakage
- **Regulatory Compliance:** Full SEBI/AMFI guideline adherence
- **Support Efficiency:** Reduced repetitive query handling
- **User Satisfaction:** High factual accuracy ratings

---

## Conclusion

This phase-wise architecture provides a comprehensive roadmap for building a compliant, accurate, and trustworthy mutual fund FAQ assistant. The emphasis on facts-over-intelligence, strict URL governance, and comprehensive guardrails ensures the system meets regulatory requirements while providing valuable factual information to users.

The modular design allows for iterative development and testing, with each phase producing demonstrable artifacts. The closed corpus approach and extensive validation layers ensure the system remains safe, accurate, and auditable throughout its lifecycle.

**Total Implementation Timeline:** 6 days  
**Key Success Factors:** Strict governance adherence, comprehensive testing, and continuous monitoring
