"""
Orchestrator Service Module - Phase 3
The central engine that wires together PII Guard, Intent Classification,
Retrieval, Reranking, Confidence Gate, Generation, and strict Post-Processing.
"""

import os
import re
import httpx
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Import governance configs
from ..config import load_disclaimer, get_scheme_mapping, get_whitelisted_urls

# Import Phase 3 components
from .pii_guard import PIIGuard
from .intent_classifier import IntentClassifier
from .refusal_composer import RefusalComposer
from ..generation.extractive import ExtractiveGenerator
from ..generation.groq_caller import GroqGenerator
from ..generation.post_processor import CompliancePostProcessor


# Import Phase 2 components
from ..retrieval.query_normalizer import QueryNormalizer
from ..retrieval.scheme_resolver import SchemeResolver
from ..retrieval.hybrid_retriever import HybridRetriever
from ..retrieval.cross_encoder_reranker import CrossEncoderReranker
from ..retrieval.confidence_gate import ConfidenceGate

logger = logging.getLogger(__name__)

class OrchestratorService:
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), '..', 'config')
        
        # Load core whitelists
        self.whitelisted_urls = get_whitelisted_urls(self.config_dir)
        self.scheme_mapping = get_scheme_mapping(self.config_dir)
        self.disclaimer = load_disclaimer(self.config_dir)
        
        # Initialize Phase 3 guardrail components
        self.pii_guard = PIIGuard(self.config_dir)
        self.intent_classifier = IntentClassifier(self.config_dir)
        self.scheme_resolver = SchemeResolver()
        self.refusal_composer = RefusalComposer(self.config_dir, self.scheme_resolver)
        
        # Initialize Phase 2 retrieval components
        self.normalizer = QueryNormalizer()
        self.retriever = HybridRetriever(self.config_dir)
        # Load indexes for retrieval
        self.retriever.load_indexes()
        
        self.reranker = CrossEncoderReranker()
        self.confidence_gate = ConfidenceGate(self.config_dir)
        
        # Banned subjective/advisory tokens (case-insensitive)
        self.banned_tokens = [
            "recommend", "invest", "outperform", "better than", "best fund", 
            "should invest", "will outperform", "superior", "guaranteed profit", 
            "massive returns", "highest return"
        ]
        
        # Safe template fallback
        self.safe_template = (
            "HDFC Mutual Fund schemes offer factual details regarding portfolio allocation, exit load, and expense ratios. "
            "For official facts, please refer directly to the scheme page: {scheme_url}\n"
            "Last updated from sources: {date}"
        )
        
        # Default fallback "I don't know" template
        self.dont_know_template = (
            "I don't have a verified answer for this query based on our locked corpus of 5 HDFC schemes. "
            "Please ask a general question about scheme exit loads, expense ratios, portfolio Details, or minimum investments."
        )

        # Initialize Phase 3 generation and post-processor components
        self.extractive_generator = ExtractiveGenerator()
        self.groq_generator = GroqGenerator()
        self.post_processor = CompliancePostProcessor(
            pii_guard=self.pii_guard,
            whitelisted_urls=self.whitelisted_urls,
            scheme_mapping=self.scheme_mapping,
            disclaimer=self.disclaimer,
            safe_template=self.safe_template,
            dont_know_template=self.dont_know_template
        )
        self._last_top_chunk_id = None


    def _get_chunk_details(self, chunk_id: str) -> Dict[str, Any]:
        """Fetch the actual text and metadata of a chunk by its chunk_id"""
        store = self.retriever.vector_store
        if not store:
            return {}
            
        # 1. If using mock store, fetch directly
        if hasattr(store, "mock_embeddings") and chunk_id in store.mock_embeddings:
            return store.mock_embeddings[chunk_id]
            
        # 2. If using real ChromaDB collection
        if store.collection:
            try:
                res = store.collection.get(ids=[chunk_id])
                if res and res.get("ids") and len(res["ids"]) > 0:
                    metadata = res["metadatas"][0] if res.get("metadatas") else {}
                    text = res["documents"][0] if res.get("documents") else ""
                    return {
                        "chunk_id": chunk_id,
                        "text": text,
                        "scheme_id": metadata.get("scheme_id", ""),
                        "section": metadata.get("section", ""),
                        "last_updated": metadata.get("last_updated", "2026-05-12")
                    }
            except Exception as e:
                logger.error(f"Error fetching chunk details from Chroma: {e}")
                
        return {}

    def ask(self, query: str, use_groq: Optional[bool] = None) -> Dict[str, Any]:
        """
        Ask a question end-to-end with reasoning, retrieval, generation, and strict guardrails.
        Measures execution latency and logs structured privacy-preserving transactions.
        """
        from datetime import datetime
        start_time = datetime.now()
        
        self._last_top_chunk_id = None
        res = self._ask_internal(query, use_groq=use_groq)
        
        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Log the transaction securely
        from ..utils.logger import log_transaction
        request_id = log_transaction(
            query=query,
            intent=res["intent"],
            resolved_scheme_id=res["scheme_id"],
            confidence_score=res["confidence"],
            top_chunk_id=self._last_top_chunk_id,
            latency_ms=latency_ms,
            compliance_checks_passed=res["checks_passed"]
        )
        res["request_id"] = request_id
        return res

    def _ask_internal(self, query: str, use_groq: Optional[bool] = None) -> Dict[str, Any]:
        """
        Internal ask logic that wires together PII Guard, Intent Classification,
        Retrieval, Reranking, Confidence Gate, Generation, and strict Post-Processing.
        """
        logger.info(f"Processing query: {query}")
        
        # 1. PII Guard Check
        if self.pii_guard.detect(query):
            redacted_query = self.pii_guard.redact(query)
            logger.warning(f"Query blocked by PII Guard. Redacted: '{redacted_query}'")
            return {
                "answer": self.pii_guard.pii_block_response.strip(),
                "source_url": None,
                "intent": "pii_blocked",
                "confidence": 0.0,
                "checks_passed": True,
                "scheme_id": None
            }
            
        # 2. Intent Classification
        intent = self.intent_classifier.classify(query)
        if intent != "factual":
            logger.info(f"Advisory/refusal intent detected: '{intent}'")
            refusal_ans = self.refusal_composer.compose(query, intent)
            
            # Post-process refusal URL count
            urls = re.findall(r'https?://\S+', refusal_ans)
            
            # Validate URL count
            if len(urls) != 1 or urls[0] not in self.whitelisted_urls:
                logger.warning(f"Refusal response URL check failed (URLs: {urls}). Using safe template.")
                resolved_scheme_id = self.scheme_resolver.resolve(query) or "hdfc_equity"
                scheme_url = self.scheme_mapping.get(resolved_scheme_id, self.whitelisted_urls[0])
                refusal_ans = self.safe_template.format(scheme_url=scheme_url, date="2026-05-12")
                
            return {
                "answer": refusal_ans.strip(),
                "source_url": re.findall(r'https?://\S+', refusal_ans)[0] if re.findall(r'https?://\S+', refusal_ans) else None,
                "intent": intent,
                "confidence": 0.0,
                "checks_passed": True,
                "scheme_id": self.scheme_resolver.resolve(query)
            }
            
        # 3. Query Normalization & Scheme Resolution
        norm_res = self.normalizer.normalize_query(query)
        normalized_query = norm_res["normalized_query"]
        
        scheme_res = self.scheme_resolver.detect_scheme_terms(normalized_query)
        detected_schemes = scheme_res["detected_schemes"]
        resolved_scheme_id = detected_schemes[0] if detected_schemes else None
        
        # 4. Hybrid Retrieval
        scheme_filter = [resolved_scheme_id] if resolved_scheme_id else None
        retrieved_results = self.retriever.retrieve(
            query=normalized_query,
            scheme_filter=scheme_filter,
            top_k=10
        )
        
        if not retrieved_results:
            logger.warning("No retrieval results returned by Hybrid Retriever")
            return self._build_dont_know_response()
            
        # 5. Fetch Candidate Text & Details
        candidates = []
        for result in retrieved_results:
            # retrieved_results is a list of tuples: (chunk_id, fused_score, source)
            chunk_id, score, source = result
            chunk_details = self._get_chunk_details(chunk_id)
            if chunk_details:
                candidates.append({
                    "chunk_id": chunk_id,
                    "text": chunk_details["text"],
                    "score": score,
                    "source": source,
                    "scheme_id": chunk_details["scheme_id"],
                    "section": chunk_details["section"],
                    "last_updated": chunk_details.get("last_updated", "2026-05-12")
                })
                
        if not candidates:
            logger.warning("No candidate texts could be fetched")
            return self._build_dont_know_response()
            
        # 6. Re-ranking
        reranked = self.reranker.rerank(normalized_query, candidates, top_k=3)
        
        # Format for confidence gate
        reranked_candidates = []
        for res in reranked:
            idx, score, source, chunk_id = res
            original_cand = candidates[idx]
            original_cand["score"] = score
            original_cand["source"] = source
            reranked_candidates.append(original_cand)
            
        # 7. Confidence Gate
        gated_results = self.confidence_gate.filter_by_confidence(reranked_candidates)
        top_winner = gated_results[0]
        
        if top_winner.get("chunk_id") == "fallback":
            logger.warning("Confidence gate triggered fallback")
            return self._build_dont_know_response()
            
        self._last_top_chunk_id = top_winner.get("chunk_id")
        
        # 8. Generation (Factual synthesis)
        chunk_text = top_winner["text"]
        scheme_id = top_winner["scheme_id"]
        scheme_url = self.scheme_mapping.get(scheme_id, self.whitelisted_urls[0])
        last_updated_date = top_winner.get("last_updated", "2026-05-12")
        confidence_score = top_winner["score"]
        
        # Decide if we use Groq LLM or Extractive Fallback
        groq_api_key = os.getenv("GROQ_API_KEY")
        groq_enabled = use_groq is True or (use_groq is not False and bool(groq_api_key))
        
        draft_answer = ""
        generation_mode = "extractive"
        
        if groq_enabled:
            try:
                draft_answer = self._call_groq_completions(normalized_query, chunk_text, groq_api_key)
                generation_mode = "groq"
                logger.info("Successfully generated answer via Groq API")
            except Exception as e:
                logger.error(f"Groq generation failed ({e}). Falling back to extractive.")
                draft_answer = self._generate_extractive(chunk_text)
        else:
            draft_answer = self._generate_extractive(chunk_text)
            
        # 9. Compliance Engine (Post-Processor)
        final_answer, checks_passed = self._run_compliance_post_processor(
            draft_answer=draft_answer,
            chunk_text=chunk_text,
            scheme_url=scheme_url,
            date=last_updated_date,
            generation_mode=generation_mode
        )
        
        return {
            "answer": final_answer,
            "source_url": scheme_url,
            "intent": "factual",
            "confidence": confidence_score,
            "checks_passed": checks_passed,
            "scheme_id": scheme_id
        }

    def _call_groq_completions(self, query: str, context: str, api_key: str) -> str:
        """Call Groq API with low temperature and strict groundedness instructions"""
        return self.groq_generator.generate(query=query, context=context, api_key=api_key)

    def _generate_extractive(self, chunk_text: str) -> str:
        """Fallback extractive generation: get first <= 3 sentences of chunk"""
        return self.extractive_generator.generate(chunk_text=chunk_text)

    def _run_compliance_post_processor(self, draft_answer: str, chunk_text: str, scheme_url: str, date: str, generation_mode: str) -> Tuple[str, bool]:
        """
        Runs rigorous post-checks to guarantee ≤ 3 sentences, banned token filtering,
        exact URL rules, date footer, and secondary PII scans.
        """
        return self.post_processor.process(
            draft_answer=draft_answer,
            chunk_text=chunk_text,
            scheme_url=scheme_url,
            date=date,
            generation_mode=generation_mode
        )


    def _build_dont_know_response(self) -> Dict[str, Any]:
        """Builds a compliant low-confidence 'I don't know' response with exactly 0 URLs"""
        return {
            "answer": self.dont_know_template.strip(),
            "source_url": None,
            "intent": "dont_know",
            "confidence": 0.0,
            "checks_passed": True,
            "scheme_id": None
        }
