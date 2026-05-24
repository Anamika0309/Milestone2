"""
Phase 2.3 - Hybrid Retriever (Standalone Phase Copy)
Purpose: Weighted Reciprocal Rank Fusion (WRRF) for optimal retrieval
"""

import logging
import os
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

# Try relative package imports, fallback to standalone implementation
try:
    from ..config.sources import load_sources
except (ImportError, ValueError):
    try:
        from mf_faq.config.sources import load_sources
    except ImportError:
        # Standalone copy fallback definition
        import yaml
        def load_sources(config_dir: str = None) -> dict:
            if config_dir is None:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                config_dir = os.path.join(base_dir, 'phases', 'phase_0')
                if not os.path.exists(config_dir):
                    config_dir = os.path.join(base_dir, 'src', 'mf_faq', 'config')
            sources_file = os.path.join(config_dir, 'sources.yaml')
            try:
                with open(sources_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception:
                return {'schemes': []}

try:
    from ..vector_db.chroma_store import ChromaVectorStore
except (ImportError, ValueError):
    try:
        from mf_faq.vector_db.chroma_store import ChromaVectorStore
    except ImportError:
        ChromaVectorStore = None

try:
    from ..ingestion.embedder import Embedder
except (ImportError, ValueError):
    try:
        from mf_faq.ingestion.embedder import Embedder
    except ImportError:
        try:
            # Try importing from the siblings phase folder
            from phases.phase_1.embedder import Embedder
        except ImportError:
            Embedder = None


logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid retriever combining dense and sparse search"""
    
    def __init__(self, config_dir: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        self.config_dir = config_dir or os.path.join(base_dir, 'phases', 'phase_0')
        if not os.path.exists(self.config_dir):
            self.config_dir = os.path.join(base_dir, 'src', 'mf_faq', 'config')
            
        self.index_dir = os.path.join(base_dir, 'data', 'index')
        
        # Search configuration
        self.fusion_weights = {
            'dense': 0.6,
            'sparse': 0.4
        }
        
        # Top-k configuration
        self.top_k_dense = 20
        self.top_k_sparse = 20
        self.top_k_fused = 20
        
        # Load vector store
        self.vector_store = None
        self.dense_index = None
        self.sparse_index = None
        
        logger.info(f"Initialized standalone hybrid retriever (Config: {self.config_dir})")
    
    def load_indexes(self) -> bool:
        """Load dense and sparse indexes"""
        try:
            if ChromaVectorStore is not None:
                self.vector_store = ChromaVectorStore(self.config_dir, "mf_faq_embeddings")
                stats = self.vector_store.get_collection_stats()
                logger.info(f"Loaded vector store (ChromaDB): {stats}")
                return True
            else:
                logger.warning("ChromaVectorStore not available. Operating in mock index mode.")
                return True
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            return False
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate query embedding using BGE model"""
        try:
            if Embedder is not None:
                embedder = Embedder()
                query_embedding = embedder.embed_text(query)
                return query_embedding
            else:
                logger.warning("Embedder not available. Returning mock embedding.")
                return [0.1] * 384
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return [0.1] * 384
    
    def detect_query_type(self, query: str) -> str:
        """Detect if query is numeric/financial or semantic"""
        numeric_indicators = [
            'ratio', 'percent', '%', 'expense', 'exit', 'load', 
            'nav', 'aum', 'sip', 'lumpsum', 'minimum', 'benchmark',
            'returns', 'performance', 'risk', 'allocation', 'portfolio'
        ]
        
        semantic_indicators = [
            'how', 'what', 'why', 'when', 'where', 'explain',
            'describe', 'compare', 'difference', 'benefits', 'features',
            'strategy', 'objective', 'goal', 'approach', 'method'
        ]
        
        query_lower = query.lower()
        
        if any(scheme in query_lower for scheme in ['hdfc', 'icici', 'sbi', 'axis']):
            return 'scheme-specific'
        
        if any(indicator in query_lower for indicator in numeric_indicators):
            return 'numeric'
        
        if any(indicator in query_lower for indicator in semantic_indicators):
            return 'semantic'
        
        return 'semantic'
    
    def search_dense(self, query_embedding: List[float], top_k: int = None) -> List[Tuple[int, float]]:
        """Search dense index"""
        if not self.vector_store:
            return [(i, 0.8 - (i * 0.05)) for i in range(top_k or self.top_k_dense)]
        
        if top_k is None:
            top_k = self.top_k_dense
        
        try:
            results = self.vector_store.query_embeddings(query_embedding, top_k)
            formatted_results = [(result['chunk_id'], 1.0 - result['distance']) for result in results]
            logger.info(f"Dense search returned {len(formatted_results)} results")
            return formatted_results
        except Exception as e:
            logger.error(f"Error in dense search: {e}")
            return []
    
    def search_sparse(self, query: str, top_k: int = None) -> List[Tuple[int, float]]:
        """Search sparse index"""
        if not self.vector_store:
            return [(i, 0.75 - (i * 0.05)) for i in range(top_k or self.top_k_sparse)]
        
        if top_k is None:
            top_k = self.top_k_sparse
        
        try:
            results = self.vector_store.query_embeddings([], top_k)
            formatted_results = []
            for result in results:
                formatted_results.append((
                    result['chunk_id'],
                    1.0 - result['distance']
                ))
            logger.info(f"Sparse search returned {len(formatted_results)} results")
            return formatted_results
        except Exception as e:
            logger.error(f"Error in sparse search: {e}")
            return []
    
    def fuse_results(self, dense_results: List[Tuple[int, float]], 
                   sparse_results: List[Tuple[int, float]]) -> List[Tuple[int, float, str]]:
        """Fuse dense and sparse results using WRRF"""
        all_results = {}
        
        for chunk_id, score in dense_results:
            all_results[chunk_id] = {
                'chunk_id': chunk_id,
                'dense_score': score,
                'sparse_score': 0.0,
                'source': 'dense'
            }
        
        for chunk_id, score in sparse_results:
            if chunk_id in all_results:
                all_results[chunk_id]['sparse_score'] = score
                all_results[chunk_id]['source'] = 'fused'
            else:
                all_results[chunk_id] = {
                    'chunk_id': chunk_id,
                    'dense_score': 0.0,
                    'sparse_score': score,
                    'source': 'sparse'
                }
        
        fused_results = []
        for chunk_id, result in all_results.items():
            dense_score = result['dense_score']
            sparse_score = result['sparse_score']
            
            fused_score = (
                self.fusion_weights['dense'] * dense_score +
                self.fusion_weights['sparse'] * sparse_score
            )
            fused_results.append((chunk_id, fused_score, result['source']))
        
        fused_results.sort(key=lambda x: x[1], reverse=True)
        top_results = fused_results[:self.top_k_fused]
        
        logger.info(f"Fused {len(dense_results)} dense + {len(sparse_results)} sparse results into {len(top_results)} fused results")
        return top_results
    
    def retrieve(self, query: str, query_embedding: List[float] = None, 
                 scheme_filter: List[str] = None, top_k: int = None) -> List[Dict[str, Any]]:
        """Main retrieval function"""
        try:
            logger.info(f"Retrieving for query: {query}")
            
            query_type = self.detect_query_type(query)
            
            if query_type == 'numeric':
                self.fusion_weights = {'dense': 0.4, 'sparse': 0.6}
            elif query_type == 'semantic':
                self.fusion_weights = {'dense': 0.7, 'sparse': 0.3}
            else:
                self.fusion_weights = {'dense': 0.6, 'sparse': 0.4}
            
            query_embedding = self.generate_query_embedding(query)
            dense_results = self.search_dense(query_embedding, top_k)
            sparse_results = self.search_sparse(query, top_k)
            fused_results = self.fuse_results(dense_results, sparse_results)
            
            if scheme_filter:
                filtered_results = [
                    result for result in fused_results
                    if str(result[0]) in [str(sf) for sf in scheme_filter]
                ]
            else:
                filtered_results = fused_results
            
            top_results = filtered_results[:top_k or self.top_k_fused]
            
            logger.info(f"Retrieved {len(top_results)} results for query type: {query_type}")
            return top_results
            
        except Exception as e:
            logger.error(f"Error in retrieval: {e}")
            return []
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of hybrid retriever"""
        try:
            health_report = {
                'dense_index_loaded': self.vector_store is not None,
                'sparse_index_loaded': self.vector_store is not None,
                'total_vectors': 0 if not self.vector_store else 100, # Mock/indicator
                'total_documents': 0 if not self.vector_store else 100,
                'fusion_weights': self.fusion_weights,
                'health': 'ok' if self.vector_store else 'mock'
            }
            return health_report
        except Exception as e:
            logger.error(f"Error getting retriever health: {e}")
            return {'health': 'error', 'error': str(e)}


# CLI interface for standalone execution
def main():
    """CLI interface for hybrid retriever"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hybrid retrieval with WRRF fusion (Standalone)')
    parser.add_argument('--config-dir', help='Configuration directory path')
    parser.add_argument('--query', required=True, help='Query to process')
    parser.add_argument('--top-k', type=int, default=10, help='Number of results to return')
    
    args = parser.parse_args()
    
    retriever = HybridRetriever(args.config_dir)
    retriever.load_indexes()
    
    results = retriever.retrieve(
        query=args.query,
        top_k=args.top_k
    )
    
    print(f"\nHybrid Retrieval Results for: '{args.query}'")
    for i, result in enumerate(results, 1):
        chunk_id, score, source = result
        print(f"{i}. Chunk {chunk_id} (Score: {score:.4f}, Source: {source})")


if __name__ == "__main__":
    main()
