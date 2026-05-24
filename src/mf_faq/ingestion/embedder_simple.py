"""
Phase 1.5 - Simple Embedder Module (No Heavy Dependencies)
Purpose: Generate embeddings for chunks using mock implementation for testing

Strategy:
- Mock embeddings for testing Phase 1.5 structure
- Persist model metadata alongside vectors
- 384-dimensional vectors (mocked)

Outputs:
- `data/index/embeddings.parquet`
- `embedder.json` (model metadata)

Exit Criteria: All chunks have embeddings, model version tracked
"""

import json
import logging
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SimpleEmbedder:
    """Simple embedder class for testing without heavy dependencies"""
    
    def __init__(self, config_dir: str = None, model_name: str = "mock-bge-small-en"):
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), '..', 'config')
        self.input_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'processed')
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'index')
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Model configuration
        self.model_name = model_name
        self.embedding_dim = 384  # bge-small-en dimension
        
        logger.info(f"Initialized simple embedder with model: {self.model_name}")
    
    def prepare_text_for_embedding(self, chunk: Dict[str, Any]) -> str:
        """Prepare text for embedding with scheme name prefix"""
        scheme_name = chunk.get('scheme_name', '')
        text = chunk.get('text', '')
        
        # Use scheme name prefix to avoid boilerplate clustering
        embedding_text = f"{scheme_name}\n\n{text}"
        
        return embedding_text.strip()
    
    def generate_mock_embeddings(self, chunks: List[Dict[str, Any]]) -> List[List[float]]:
        """Generate mock embeddings for a list of chunks"""
        logger.info(f"Generating mock embeddings for {len(chunks)} chunks")
        
        embeddings = []
        for i, chunk in enumerate(chunks):
            # Generate deterministic mock embeddings based on chunk content
            text = self.prepare_text_for_embedding(chunk)
            seed = hash(text) % (2**32)  # Deterministic seed
            
            random.seed(seed)
            embedding = [random.uniform(-1, 1) for _ in range(self.embedding_dim)]
            
            # Normalize embedding
            norm = sum(x*x for x in embedding) ** 0.5
            if norm > 0:
                embedding = [x/norm for x in embedding]
            
            embeddings.append(embedding)
        
        logger.info(f"Successfully generated {len(embeddings)} mock embeddings")
        return embeddings
    
    def save_embeddings(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> bool:
        """Save embeddings to parquet file"""
        try:
            # Prepare data for parquet
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
            
            # Save to JSON for now (parquet requires pandas which we have)
            embeddings_file = os.path.join(self.output_dir, 'embeddings.json')
            with open(embeddings_file, 'w', encoding='utf-8') as f:
                json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(embeddings_data)} embeddings to {embeddings_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving embeddings: {e}")
            return False
    
    def save_model_metadata(self) -> bool:
        """Save model metadata to JSON file"""
        try:
            metadata = {
                'model_name': self.model_name,
                'model_version': 'mock-1.0',
                'embedding_dim': self.embedding_dim,
                'max_seq_length': 512,
                'normalized_embeddings': True,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'total_chunks': 0,  # Will be updated after processing
                'embedding_strategy': 'scheme_name_prefix',
                'note': 'Mock implementation for testing Phase 1.5 structure'
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
            embeddings = self.generate_mock_embeddings(chunks)
            
            # Save embeddings
            if self.save_embeddings(chunks, embeddings):
                logger.info(f"Processed {len(chunks)} chunks from {chunks_file_path}")
                return True
            else:
                logger.error("Failed to save embeddings")
                return False
            
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
        embeddings = self.generate_mock_embeddings(all_chunks)
        
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
        """Get overall health status of embedder"""
        try:
            health_report = {
                'model_loaded': True,
                'model_name': self.model_name,
                'embedding_dim': self.embedding_dim,
                'total_chunks': 0,
                'embeddings_file_exists': False,
                'metadata_file_exists': False,
                'last_embedding_time': None,
                'health': 'unknown'
            }
            
            # Check files
            embeddings_file = os.path.join(self.output_dir, 'embeddings.json')  # Using JSON for now
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
    """CLI interface for embedder"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate embeddings for chunks')
    parser.add_argument('--config-dir', help='Configuration directory path')
    parser.add_argument('--input-dir', help='Input directory with chunk files')
    parser.add_argument('--output-dir', help='Output directory for embeddings')
    parser.add_argument('--model-name', default='mock-bge-small-en', help='Model name for embeddings')
    parser.add_argument('--chunks-file', help='Specific chunks file to process')
    
    args = parser.parse_args()
    
    embedder = SimpleEmbedder(args.config_dir, args.model_name)
    
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
