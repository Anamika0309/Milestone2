# Phase 1: Ingestion Pipeline

This phase is responsible for crawler ingestion, content extraction, text cleaning, chunks preparation, and embedding generation, culminating in both sparse and dense indices.

## Steps in the Pipeline

1. **Fetcher (`fetcher.py`)**
   - Implements robust web scraping of the 5 whitelisted Groww URLs.
   - Includes full compliant `robots.txt` checks and rate-limiting.
   - Uses HTTP ETags for delta updates (304 Not Modified support).
   - Gracefully falls back to headless Playwright if standard HTTP requests are blocked or fail.

2. **Extractor (`extractor.py`)**
   - Strips generic boilerplate HTML (headers, footers, sidebars).
   - Identifies and isolates key financial tables and core scheme data.
   - Extracts structured key-value maps for attributes like Expense Ratios, Exit Loads, and AUM.

3. **Cleaner (`cleaner.py`)**
   - Performs Unicode normalization (NFKC) to resolve special characters.
   - Standardizes currency strings (e.g., converting `Rs.`, `Rupees`, `INR` to `₹`).
   - Discards non-factual, highly volatile manager commentaries, leaving clean facts.

4. **Chunker (`chunker.py`)**
   - Implements structured chunking with soft/hard cap limits.
   - Preserves sentences and tabular bounds to avoid cutting critical financial tables in half.
   - Adds metadata overlaps to prevent context loss at transition borders.

5. **Embedder (`embedder.py`)**
   - Generates high-quality dense vector representations of each text chunk.
   - Uses `BAAI/bge-small-en` (384-dimensional space) for maximum speed and accuracy.
   - Insulated against PyTorch/SentenceTransformers DLL crashes with full mock fallbacks.

6. **Indexer (`indexer.py`)**
   - Generates both **Dense (FAISS)** and **Sparse (BM25Okapi)** search indices.
   - Saves final binary indices to disk (`dense_index.faiss` and `sparse_index.pkl`) along with indexer metadata (`indexer.json`).
   - Supports seamless mock modes to run cleanly in clean environment setups.
