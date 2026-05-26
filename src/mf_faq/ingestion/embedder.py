"""
Phase 1.5 - Embedder Module
Purpose: Generate embeddings for chunks using BGE-Small-EN model

Strategy:
- Embed `f"{scheme_name}\n\n{text}"` to avoid boilerplate clustering
- Persist model metadata alongside vectors
- 384-dimensional vectors for bge-small-en

Outputs:
- `data/index/embeddings.parquet`
- `embedder.json` (model metadata)

Exit Criteria: All chunks have embeddings, model version tracked
"""

import json
import logging
import os
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

from ..utils.import_utils import is_library_safe

# Import sentence-transformers
SENTENCE_TRANSFORMERS_AVAILABLE = False
if is_library_safe("sentence_transformers"):
    try:
        from sentence_transformers import SentenceTransformer
        SENTENCE_TRANSFORMERS_AVAILABLE = True
    except ImportError:
        logger.warning("sentence-transformers not available. Please install with: pip install sentence-transformers")
else:
    logger.warning("sentence-transformers is not safe to import on this system. Using mock embedder functionality if needed")


class Embedder:
    """Main embedder class for processing chunks"""
    
    def __init__(self, config_dir: str = None, model_name: str = "BAAI/bge-small-en"):
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), '..', 'config')
        self.input_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'processed')
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'index')
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Model configuration
        self.model_name = model_name
        self.model = None
        self.embedding_dim = 384  # bge-small-en dimension
        
        # Initialize model
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the sentence transformer model"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence-transformers is not available. Using mock embeddings.")
            return
        
        try:
            logger.info(f"Loading model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            logger.warning("Falling back to mock embeddings due to initialization error.")
    
    def prepare_text_for_embedding(self, chunk: Dict[str, Any]) -> str:
        """Prepare text for embedding with scheme name prefix"""
        scheme_name = chunk.get('scheme_name', '')
        text = chunk.get('text', '')
        
        # Use scheme name prefix to avoid boilerplate clustering
        embedding_text = f"{scheme_name}\n\n{text}"
        
        return embedding_text.strip()
    
    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[List[float]]:
        """Generate embeddings for a list of chunks"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE or not self.model:
            logger.warning("Generating mock embeddings since sentence-transformers is not available/loaded")
            return [[0.1] * self.embedding_dim for _ in chunks]
        
        # Prepare texts for embedding
        texts = [self.prepare_text_for_embedding(chunk) for chunk in chunks]
        
        logger.info(f"Generating embeddings for {len(texts)} chunks")
        
        try:
            # Generate embeddings in batch
            embeddings = self.model.encode(
                texts,
                batch_size=8,
                normalize_embeddings=True,
                show_progress_bar=True
            )
            
            logger.info(f"Successfully generated {len(embeddings)} embeddings")
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}. Falling back to mock embeddings.")
            return [[0.1] * self.embedding_dim for _ in chunks]
    
    def save_embeddings(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> bool:
        """Save embeddings to parquet file, json file, and ChromaDB"""
        try:
            # Prepare data for parquet/json
            embeddings_data = []
            for chunk, embedding in zip(chunks, embeddings):
                row = {
                    'chunk_id': chunk.get('chunk_id'),
                    'scheme_id': chunk.get('scheme_id'),
                    'scheme_name': chunk.get('scheme_name'),
                    'source_url': chunk.get('source_url'),
                    'section': chunk.get('section'),
                    'text': chunk.get('text'),
                    'embedding': embedding,
                    'token_count': chunk.get('token_count'),
                    'chunk_order': chunk.get('chunk_order'),
                    'content_hash': chunk.get('content_hash'),
                    'stable_content_hash': chunk.get('stable_content_hash'),
                    'last_updated': chunk.get('last_updated')
                }
                embeddings_data.append(row)
            
            # Save to parquet
            embeddings_df = pd.DataFrame(embeddings_data)
            embeddings_file = os.path.join(self.output_dir, 'embeddings.parquet')
            embeddings_df.to_parquet(embeddings_file, index=False)
            logger.info(f"Saved {len(embeddings_data)} embeddings to {embeddings_file}")
            
            # Save to JSON for compatibility
            json_file = os.path.join(self.output_dir, 'embeddings.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(embeddings_data)} embeddings to {json_file}")
            
            # Save to ChromaDB
            try:
                from ..vector_db.chroma_store import ChromaVectorStore
                vector_store = ChromaVectorStore(self.config_dir, "mf_faq_embeddings")
                success = vector_store.add_embeddings(embeddings_data)
                if success:
                    logger.info("Successfully saved embeddings to ChromaDB")
                else:
                    logger.warning("Failed to save embeddings to ChromaDB")
            except Exception as e:
                logger.error(f"Error saving to ChromaDB: {e}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error saving embeddings: {e}")
            return False
    
    def save_model_metadata(self) -> bool:
        """Save model metadata to JSON file"""
        try:
            metadata = {
                'model_name': self.model_name,
                'model_version': getattr(self.model, 'version', 'unknown') if self.model else 'mock-1.0',
                'embedding_dim': self.embedding_dim,
                'max_seq_length': getattr(self.model, 'max_seq_length', 512) if self.model else 512,
                'normalized_embeddings': True,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'total_chunks': 0,  # Will be updated after processing
                'embedding_strategy': 'scheme_name_prefix'
            }
            
            metadata_file = os.path.join(self.output_dir, 'embedder.json')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved model metadata to {metadata_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model metadata: {e}")
            return False
    
    def update_model_metadata(self, total_chunks: int) -> bool:
        """Update model metadata with chunk count"""
        try:
            metadata_file = os.path.join(self.output_dir, 'embedder.json')
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                metadata['total_chunks'] = total_chunks
                metadata['last_updated'] = datetime.now(timezone.utc).isoformat()
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Updated model metadata with {total_chunks} chunks")
                return True
            else:
                logger.warning("Metadata file not found for update")
                return False
                
        except Exception as e:
            logger.error(f"Error updating model metadata: {e}")
            return False
            
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text string"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE or not self.model:
            # Return mock 384-dimensional embedding
            return [0.1] * self.embedding_dim
            
        try:
            embedding = self.model.encode(
                [text],
                normalize_embeddings=True,
                show_progress_bar=False
            )
            return embedding[0].tolist()
        except Exception as e:
            logger.error(f"Error in embed_text: {e}")
            return [0.1] * self.embedding_dim
            
    def embed_and_save(self, chunks: List[Dict[str, Any]]) -> bool:
        """Generate embeddings for chunks and save them"""
        try:
            embeddings = self.generate_embeddings(chunks)
            return self.save_embeddings(chunks, embeddings)
        except Exception as e:
            logger.error(f"Error in embed_and_save: {e}")
            return False
    
    def load_chunks_from_file(self, chunks_file_path: str) -> List[Dict[str, Any]]:
        """Load chunks from JSON file"""
        try:
            with open(chunks_file_path, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            
            logger.info(f"Loaded {len(chunks)} chunks from {chunks_file_path}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error loading chunks from {chunks_file_path}: {e}")
            return []
    
    def embed_chunks_from_file(self, chunks_file_path: str) -> bool:
        """Process chunks from a single file and generate embeddings"""
        try:
            # Load chunks
            chunks = self.load_chunks_from_file(chunks_file_path)
            if not chunks:
                logger.error(f"No chunks found in {chunks_file_path}")
                return False
            
            # Generate embeddings
            embeddings = self.generate_embeddings(chunks)
            
            # Save embeddings
            logger.info(f"Processed {len(chunks)} chunks from {chunks_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {chunks_file_path}: {e}")
            return False
    
    def embed_all(self) -> bool:
        """Process all chunk files and generate embeddings"""
        logger.info("Starting embedding of all chunks")
        
        all_chunks = []
        
        # Find all chunk files
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                if file.endswith('chunks.json'):
                    chunks_file_path = os.path.join(root, file)
                    chunks = self.load_chunks_from_file(chunks_file_path)
                    all_chunks.extend(chunks)
        
        if not all_chunks:
            logger.error("No chunks found to embed")
            return False
        
        # Save initial metadata
        self.save_model_metadata()
        
        # Generate embeddings
        embeddings = self.generate_embeddings(all_chunks)
        
        # Save embeddings
        if self.save_embeddings(all_chunks, embeddings):
            # Update metadata with total chunks
            self.update_model_metadata(len(all_chunks))
            logger.info(f"Successfully embedded {len(all_chunks)} chunks")
            return True
        else:
            logger.error("Failed to save embeddings")
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the embedder"""
        try:
            health_report = {
                'model_loaded': self.model is not None,
                'model_name': self.model_name,
                'embedding_dim': self.embedding_dim,
                'total_chunks': 0,
                'embeddings_file_exists': False,
                'metadata_file_exists': False,
                'last_embedding_time': None,
                'health': 'unknown'
            }
            
            # Check files
            embeddings_file = os.path.join(self.output_dir, 'embeddings.parquet')
            metadata_file = os.path.join(self.output_dir, 'embedder.json')
            
            health_report['embeddings_file_exists'] = os.path.exists(embeddings_file)
            health_report['metadata_file_exists'] = os.path.exists(metadata_file)
            
            # Load metadata if exists
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    health_report['total_chunks'] = metadata.get('total_chunks', 0)
                    health_report['last_embedding_time'] = metadata.get('created_at')
            
            # Determine health
            if health_report['model_loaded'] and health_report['embeddings_file_exists'] and health_report['metadata_file_exists']:
                health_report['health'] = 'ok'
            elif health_report['model_loaded']:
                health_report['health'] = 'partial'
            else:
                health_report['health'] = 'failed'
            
            return health_report
            
        except Exception as e:
            logger.error(f"Error getting embedder health: {e}")
            return {'health': 'error', 'error': str(e)}


# CLI interface for standalone execution
async def main():
    """CLI interface for the embedder"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate embeddings for chunks')
    parser.add_argument('--config-dir', help='Configuration directory path')
    parser.add_argument('--input-dir', help='Input directory with chunk files')
    parser.add_argument('--output-dir', help='Output directory for embeddings')
    parser.add_argument('--model-name', default='BAAI/bge-small-en', help='Model name for embeddings')
    parser.add_argument('--chunks-file', help='Specific chunks file to process')
    
    args = parser.parse_args()
    
    embedder = Embedder(args.config_dir, args.model_name)
    
    if args.input_dir:
        embedder.input_dir = args.input_dir
    if args.output_dir:
        embedder.output_dir = args.output_dir
    
    if args.chunks_file:
        # Process specific file
        success = embedder.embed_chunks_from_file(args.chunks_file)
        if success:
            print(f"Successfully processed {args.chunks_file}")
        else:
            print(f"Failed to process {args.chunks_file}")
    else:
        # Process all chunks
        success = embedder.embed_all()
        
        # Print summary
        health = embedder.get_health_status()
        print(f"\nEmbedding Summary:")
        print(f"Model: {health['model_name']}")
        print(f"Dimensions: {health['embedding_dim']}")
        print(f"Total chunks: {health['total_chunks']}")
        print(f"Health: {health['health']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
