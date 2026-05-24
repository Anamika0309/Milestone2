"""
Phase 1.6 - Indexer Module (Standalone Phase Copy)
Purpose: Build dense and sparse indexes for efficient retrieval
Tech Stack: FAISS (dense) + rank-bm25 (sparse)
"""

import json
import logging
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path
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

# Import FAISS and BM25 with fallbacks
FAISS_AVAILABLE = False
if is_library_safe("faiss"):
    try:
        import faiss
        FAISS_AVAILABLE = True
    except ImportError:
        logger.warning("FAISS not available. Using mock dense index")
else:
    logger.warning("faiss is not safe to import on this system. Using mock dense index")


try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank-bm25 not available. Using mock sparse index")


class Indexer:
    """Main indexer class for building retrieval indexes"""
    
    def __init__(self, config_dir: str = None):
        # Resolve dynamic base workspace folder paths
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        self.config_dir = config_dir or os.path.join(base_dir, 'phases', 'phase_0')
        if not os.path.exists(self.config_dir):
            self.config_dir = os.path.join(base_dir, 'src', 'mf_faq', 'config')
            
        self.input_dir = os.path.join(base_dir, 'data', 'index')
        self.output_dir = os.path.join(base_dir, 'data', 'index')
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize indexes
        self.dense_index = None
        self.sparse_index = None
        self.chunks = []
        
        logger.info(f"Initialized standalone indexer (Config: {self.config_dir}, Data: {self.input_dir})")
    
    def load_embeddings(self) -> bool:
        """Load embeddings from JSON file"""
        try:
            embeddings_file = os.path.join(self.input_dir, 'embeddings.json')
            if not os.path.exists(embeddings_file):
                logger.error(f"Embeddings file not found: {embeddings_file}")
                return False
            
            with open(embeddings_file, 'r', encoding='utf-8') as f:
                self.chunks = json.load(f)
            
            logger.info(f"Loaded {len(self.chunks)} chunks with embeddings")
            return True
            
        except Exception as e:
            logger.error(f"Error loading embeddings: {e}")
            return False
    
    def build_dense_index(self) -> bool:
        """Build FAISS dense index"""
        if not FAISS_AVAILABLE:
            # Create mock dense index
            self.dense_index = MockDenseIndex()
            logger.info("Created mock dense index (FAISS not available)")
            return True
        
        try:
            # Extract embeddings
            embeddings = [chunk['embedding'] for chunk in self.chunks]
            if not embeddings:
                logger.error("No embeddings found for dense indexing")
                return False
            
            # Convert to numpy array
            import numpy as np
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Build FAISS index
            dimension = embeddings_array.shape[1]
            self.dense_index = faiss.IndexFlatIP(dimension)
            self.dense_index.add(embeddings_array)
            
            logger.info(f"Built dense index with {len(embeddings)} vectors, dimension {dimension}")
            return True
            
        except Exception as e:
            logger.error(f"Error building dense index: {e}")
            return False
    
    def build_sparse_index(self) -> bool:
        """Build BM25 sparse index"""
        if not BM25_AVAILABLE:
            # Create mock sparse index
            self.sparse_index = MockSparseIndex()
            logger.info("Created mock sparse index (rank-bm25 not available)")
            return True
        
        try:
            # Extract documents for BM25
            documents = [chunk['text'] for chunk in self.chunks]
            if not documents:
                logger.error("No documents found for sparse indexing")
                return False
            
            # Build BM25 index
            self.sparse_index = BM25Okapi(documents)
            
            logger.info(f"Built sparse index with {len(documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Error building sparse index: {e}")
            return False
    
    def save_dense_index(self) -> bool:
        """Save dense index to file"""
        try:
            if FAISS_AVAILABLE and self.dense_index:
                dense_index_file = os.path.join(self.output_dir, 'dense_index.faiss')
                faiss.write_index(self.dense_index, dense_index_file)
                logger.info(f"Saved dense index to {dense_index_file}")
                return True
            elif hasattr(self.dense_index, 'save'):
                # Mock index
                dense_index_file = os.path.join(self.output_dir, 'dense_index.json')
                mock_data = {
                    'type': 'mock_dense',
                    'vectors': len(self.chunks),
                    'dimension': 384
                }
                with open(dense_index_file, 'w') as f:
                    json.dump(mock_data, f)
                logger.info(f"Saved mock dense index to {dense_index_file}")
                return True
            else:
                logger.error("No dense index to save")
                return False
                
        except Exception as e:
            logger.error(f"Error saving dense index: {e}")
            return False
    
    def save_sparse_index(self) -> bool:
        """Save sparse index to file"""
        try:
            if BM25_AVAILABLE and self.sparse_index:
                sparse_index_file = os.path.join(self.output_dir, 'sparse_index.pkl')
                with open(sparse_index_file, 'wb') as f:
                    pickle.dump(self.sparse_index, f)
                logger.info(f"Saved sparse index to {sparse_index_file}")
                return True
            elif hasattr(self.sparse_index, 'save'):
                # Mock index
                sparse_index_file = os.path.join(self.output_dir, 'sparse_index.json')
                mock_data = {
                    'type': 'mock_sparse',
                    'documents': len(self.chunks)
                }
                with open(sparse_index_file, 'w') as f:
                    json.dump(mock_data, f)
                logger.info(f"Saved mock sparse index to {sparse_index_file}")
                return True
            else:
                logger.error("No sparse index to save")
                return False
                
        except Exception as e:
            logger.error(f"Error saving sparse index: {e}")
            return False
    
    def save_metadata(self) -> bool:
        """Save index metadata"""
        try:
            metadata = {
                'dense_index_type': 'faiss' if FAISS_AVAILABLE else 'mock',
                'sparse_index_type': 'bm25' if BM25_AVAILABLE else 'mock',
                'total_chunks': len(self.chunks),
                'embedding_dimension': 384,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'faiss_available': FAISS_AVAILABLE,
                'bm25_available': BM25_AVAILABLE
            }
            
            metadata_file = os.path.join(self.output_dir, 'indexer.json')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved index metadata to {metadata_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
            return False
    
    def build_all_indexes(self) -> bool:
        """Build both dense and sparse indexes"""
        logger.info("Starting index building process")
        
        # Load embeddings
        if not self.load_embeddings():
            return False
        
        # Build dense index
        if not self.build_dense_index():
            return False
        
        # Build sparse index
        if not self.build_sparse_index():
            return False
        
        # Save indexes
        if not self.save_dense_index():
            return False
        
        if not self.save_sparse_index():
            return False
        
        # Save metadata
        if not self.save_metadata():
            return False
        
        logger.info("Successfully built all indexes")
        return True
    
    def search_dense(self, query_embedding: List[float], k: int = 5) -> List[Tuple[int, float]]:
        """Search dense index"""
        if not self.dense_index:
            return []
        
        try:
            if FAISS_AVAILABLE:
                import numpy as np
                query_array = np.array([query_embedding], dtype=np.float32)
                distances, indices = self.dense_index.search(query_array, k)
                return [(int(idx), float(dist)) for idx, dist in zip(indices[0], distances[0])]
            else:
                # Mock search
                return [(i, 0.1) for i in range(min(k, len(self.chunks)))]
        except Exception as e:
            logger.error(f"Error in dense search: {e}")
            return []
    
    def search_sparse(self, query: str, k: int = 5) -> List[Tuple[int, float]]:
        """Search sparse index"""
        if not self.sparse_index:
            return []
        
        try:
            if BM25_AVAILABLE:
                results = self.sparse_index.get_scores(query, k)
                return [(idx, float(score)) for idx, score in results]
            else:
                # Mock search
                return [(i, 0.5) for i in range(min(k, len(self.chunks)))]
        except Exception as e:
            logger.error(f"Error in sparse search: {e}")
            return []
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of indexer"""
        try:
            health_report = {
                'chunks_loaded': len(self.chunks) > 0,
                'total_chunks': len(self.chunks),
                'dense_index_built': self.dense_index is not None,
                'sparse_index_built': self.sparse_index is not None,
                'faiss_available': FAISS_AVAILABLE,
                'bm25_available': BM25_AVAILABLE,
                'index_files_exist': False,
                'health': 'unknown'
            }
            
            # Check files
            dense_file = os.path.join(self.output_dir, 'dense_index.faiss')
            sparse_file = os.path.join(self.output_dir, 'sparse_index.pkl')
            metadata_file = os.path.join(self.output_dir, 'indexer.json')
            
            health_report['index_files_exist'] = (
                (os.path.exists(dense_file) or os.path.exists(dense_file.replace('.faiss', '.json'))) and
                (os.path.exists(sparse_file) or os.path.exists(sparse_file.replace('.pkl', '.json'))) and
                os.path.exists(metadata_file)
            )
            
            # Determine health
            if (health_report['chunks_loaded'] and 
                health_report['dense_index_built'] and 
                health_report['sparse_index_built'] and 
                health_report['index_files_exist']):
                health_report['health'] = 'ok'
            elif health_report['chunks_loaded']:
                health_report['health'] = 'partial'
            else:
                health_report['health'] = 'failed'
            
            return health_report
            
        except Exception as e:
            logger.error(f"Error getting indexer health: {e}")
            return {'health': 'error', 'error': str(e)}


class MockDenseIndex:
    """Mock dense index for testing without FAISS"""
    
    def __init__(self):
        self.vectors = []
        self.save = True
    
    def add(self, vectors):
        self.vectors = vectors
    
    def search(self, query_vectors, k):
        return [[0.1] * k], [[0] * k]


class MockSparseIndex:
    """Mock sparse index for testing without BM25"""
    
    def __init__(self):
        self.documents = []
        self.save = True
    
    def get_scores(self, query, k):
        return list(range(min(k, len(self.documents))))


# CLI interface for standalone execution
def main():
    """CLI interface for indexer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build retrieval indexes (Standalone)')
    parser.add_argument('--config-dir', help='Configuration directory path')
    parser.add_argument('--input-dir', help='Input directory with embeddings')
    parser.add_argument('--output-dir', help='Output directory for indexes')
    
    args = parser.parse_args()
    
    indexer = Indexer(args.config_dir)
    
    if args.input_dir:
        indexer.input_dir = args.input_dir
    if args.output_dir:
        indexer.output_dir = args.output_dir
    
    # Build all indexes
    success = indexer.build_all_indexes()
    
    # Print summary
    health = indexer.get_health_status()
    print(f"\nIndexing Summary:")
    print(f"Total chunks: {health['total_chunks']}")
    print(f"Dense index: {'Built' if health['dense_index_built'] else 'Not built'}")
    print(f"Sparse index: {'Built' if health['sparse_index_built'] else 'Not built'}")
    print(f"FAISS available: {health['faiss_available']}")
    print(f"BM25 available: {health['bm25_available']}")
    print(f"Health: {health['health']}")


if __name__ == "__main__":
    main()
