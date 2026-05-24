"""
Phase 2.4 - Cross-encoder Re-ranker (Standalone Phase Copy)
Model: BAAI/bge-reranker-base
Purpose: Precision improvement on fused candidates
"""

import logging
import os
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# Try relative package imports, fallback to standalone implementation
try:
    from ..utils.import_utils import is_library_safe
except (ImportError, ValueError):
    try:
        from mf_faq.utils.import_utils import is_library_safe
    except ImportError:
        # Standalone copy fallback definition
        import sys
        import subprocess
        
        _IMPORT_CACHE = {}
        
        def is_library_safe(lib_name: str) -> bool:
            if lib_name in _IMPORT_CACHE:
                return _IMPORT_CACHE[lib_name]
            if os.environ.get(f"DISABLE_{lib_name.upper()}") == "1" or os.environ.get("DISABLE_ML_COMPONENTS") == "1":
                _IMPORT_CACHE[lib_name] = False
                return False
            try:
                cmd = [sys.executable, "-X", "utf8", "-c", f"import {lib_name}"]
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                is_safe = (result.returncode == 0)
                _IMPORT_CACHE[lib_name] = is_safe
                return is_safe
            except Exception:
                _IMPORT_CACHE[lib_name] = False
                return False

# Import with fallback
CROSS_ENCODER_AVAILABLE = False
if is_library_safe("sentence_transformers"):
    try:
        from sentence_transformers import CrossEncoder
        CROSS_ENCODER_AVAILABLE = True
    except (ImportError, OSError, RuntimeError, Exception) as e:
        logger.warning(f"Cross-encoder not available ({e}). Using mock re-ranker")
else:
    logger.warning("sentence-transformers is not safe to import on this system. Using mock re-ranker")


class CrossEncoderReranker:
    """Cross-encoder re-ranker for precision improvement"""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self.model = None
        self.model_loaded = False
        
        self._load_model()
    
    def _load_model(self):
        """Load cross-encoder model with fallback"""
        if not CROSS_ENCODER_AVAILABLE:
            logger.warning("Cross-encoder not available. Using mock re-ranker")
            self.model = MockCrossEncoder()
            self.model_loaded = True
            return
        
        try:
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            self.model_loaded = True
            logger.info("Cross-encoder model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {e}")
            self.model = MockCrossEncoder()
            self.model_loaded = False
    
    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 3) -> List[Tuple[int, float, str]]:
        """Re-rank candidates using cross-encoder"""
        if not self.model_loaded:
            logger.warning("Cross-encoder not loaded, using mock re-ranking")
            return [
                (i, candidates[i].get('score', 0.0), candidates[i].get('source', 'unknown'))
                for i in range(min(top_k, len(candidates)))
            ]
        
        try:
            query_text = f"query: {query}"
            candidate_texts = [candidate.get('text', '') for candidate in candidates]
            
            query_embedding = self.model.encode(query_text, convert_to_tensor=True)
            candidate_embeddings = self.model.encode(candidate_texts, convert_to_tensor=True)
            
            scores = self.model.predict(
                query_embedding.unsqueeze(0),
                candidate_embeddings,
                top_k=top_k
            )
            
            reranked_results = []
            for idx, score in enumerate(scores[0] if isinstance(scores, list) else scores):
                if idx >= len(candidates):
                    continue
                original_candidate = candidates[idx]
                reranked_results.append((
                    idx,
                    float(score),
                    original_candidate.get('source', 'unknown'),
                    original_candidate.get('chunk_id', 'unknown')
                ))
            
            logger.info(f"Re-ranked {len(reranked_results)} candidates")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Error in cross-encoder re-ranking: {e}")
            # Mock fallback re-ranking
            return [
                (i, float(0.9 - (i * 0.1)), candidates[i].get('source', 'unknown'), candidates[i].get('chunk_id', 'unknown'))
                for i in range(min(top_k, len(candidates)))
            ]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of cross-encoder re-ranker"""
        try:
            health_report = {
                'model_loaded': self.model_loaded,
                'model_name': self.model_name,
                'cross_encoder_available': CROSS_ENCODER_AVAILABLE,
                'health': 'ok' if self.model_loaded else 'mock'
            }
            return health_report
        except Exception as e:
            logger.error(f"Error getting re-ranker health: {e}")
            return {'health': 'error', 'error': str(e)}


class MockCrossEncoder:
    """Mock cross-encoder for testing without dependencies"""
    
    def __init__(self):
        self.model_name = "mock-cross-encoder"
    
    def encode(self, texts, convert_to_tensor: bool = False):
        import random
        import numpy as np
        
        if isinstance(texts, str):
            texts = [texts]
            
        embeddings = []
        for text in texts:
            seed = hash(text) % (2**32)
            random.seed(seed)
            embedding = np.random.rand(768).astype(np.float32)
            embeddings.append(embedding)
        
        return embeddings
    
    def predict(self, query_embedding, candidate_embeddings, top_k: int):
        import numpy as np
        num_candidates = len(candidate_embeddings)
        if num_candidates == 0:
            return np.array([])
        
        scores = np.random.rand(num_candidates)
        top_indices = np.argsort(scores)[-top_k:]
        return scores[top_indices]


# CLI interface for standalone execution
def main():
    """CLI interface for cross-encoder re-ranker"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Re-rank candidates using cross-encoder')
    parser.add_argument('--model-name', default='BAAI/bge-reranker-base', help='Cross-encoder model name')
    parser.add_argument('--query', required=True, help='Query for re-ranking')
    parser.add_argument('--candidates', required=True, help='Candidates to re-rank as JSON array')
    parser.add_argument('--top-k', type=int, default=3, help='Number of top results')
    
    args = parser.parse_args()
    
    reranker = CrossEncoderReranker(args.model_name)
    
    try:
        candidates = json.loads(args.candidates)
    except Exception:
        candidates = [{"text": "Candidate 1", "chunk_id": "c1", "source": "dense"},
                      {"text": "Candidate 2", "chunk_id": "c2", "source": "sparse"}]
    
    results = reranker.rerank(args.query, candidates, args.top_k)
    
    print(f"\nCross-Encoder Re-ranking Results:")
    for i, (idx, score, source, chunk_id) in enumerate(results, 1):
        print(f"{i}. Score: {score:.4f}, Source: {source}, Chunk: {chunk_id}")


if __name__ == "__main__":
    main()
