# Phase 2: Retrieval Layer

This phase is responsible for processing incoming user queries, mapping them to relevant mutual fund schemes, performing hybrid search, ranking candidates, and validating results before returning them.

## Retrieval Process & Components

1. **Query Normalizer (`query_normalizer.py`)**
   - Applies NFKC normalization and lowercases the input.
   - Standardizes common currency and percent formats (e.g. converting `Rs.` to `₹`, `percent` to `%`).
   - Expands abbreviations like `ELSS`, `SIP`, `NAV`, and `AUM` to their full descriptions for enhanced semantic retrieval.

2. **Scheme Resolver (`scheme_resolver.py`)**
   - Uses a longest-substring NER-lite matching strategy against `sources.yaml` to detect which specific schemes are mentioned in the query.
   - Applies alias maps to resolve terms like `midcap` or `tax saver` to HDFC Mid Cap or HDFC ELSS.
   - Filters and boosts retrieval scores based on section relevance (e.g. higher importance for `scheme details` and `exit load` sections).

3. **Hybrid Retriever (`hybrid_retriever.py`)**
   - Implements hybrid retrieval combining dense semantic search (ChromaDB/Embeddings) and sparse keyword search.
   - Combines candidates using Weighted Reciprocal Rank Fusion (WRRF).
   - Dynamically shifts weights depending on query type:
     - **Numeric queries** (e.g. containing "expense", "exit load", percentage metrics) boost sparse keyword matching.
     - **Semantic queries** (e.g. explanations, differences, benefits) boost dense embedding matching.

4. **Cross-Encoder Reranker (`cross_encoder_reranker.py`)**
   - Reranks top fused candidates using the precision model `BAAI/bge-reranker-base`.
   - Offers robust fallback mocks for environments without PyTorch/SentenceTransformers.

5. **Confidence Gate (`confidence_gate.py`)**
   - Evaluates reranked candidates against a confidence threshold ($\tau = 0.7$).
   - Calculates the margin between the first and second best candidates.
   - Deflects low-confidence or highly ambiguous queries to a safe refusal template ("I don't know") with exactly 0 citation URLs to avoid hallucination.
