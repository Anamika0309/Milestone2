"""
Phase 1.4 - Chunker Module
Purpose: Split cleaned sections into retrieval units with proper boundaries

Chunking Strategy:
- Filter empty sections first (FAQ dropped, volatile fields removed)
- One section → one chunk (default), with length-based splitting
- Soft cap: 250 tokens, Hard cap: 400 tokens
- Sentence boundary splitting (never mid-fact)
- Preserve atomic table rows from financial data
- Merge sections under 50 tokens with related content
- Expected output: 5-7 chunks per scheme → 25-35 total
"""

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .cleaner import CleanedDoc


logger = logging.getLogger(__name__)


class Chunk:
    """Represents a single chunk of content"""
    
    def __init__(self, chunk_id: str, scheme_id: str, scheme_name: str, source_url: str,
                 section: str, text: str, token_count: int, chunk_order: int,
                 content_hash: str, stable_content_hash: str, last_updated: str):
        self.chunk_id = chunk_id
        self.scheme_id = scheme_id
        self.scheme_name = scheme_name
        self.source_url = source_url
        self.section = section
        self.text = text
        self.token_count = token_count
        self.chunk_order = chunk_order
        self.content_hash = content_hash
        self.stable_content_hash = stable_content_hash
        self.last_updated = last_updated


class Chunker:
    """Main chunker class for processing cleaned documents"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), '..', 'config')
        self.input_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'processed')
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'processed')
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Token estimation (rough approximation)
        self.token_chars = 4  # Average characters per token
        
        # Short section threshold
        self.min_token_threshold = 50
        
        # Soft and hard caps
        self.soft_cap = 250
        self.hard_cap = 400
    
    def estimate_token_count(self, text: str) -> int:
        """Estimate token count based on character count"""
        return len(text) // self.token_chars
    
    def is_empty_section(self, section_name: str, section_text: str) -> bool:
        """Check if section should be skipped"""
        # FAQ sections are dropped entirely
        if section_name.lower() == 'faq':
            return True
        
        # Empty or very short sections
        if not section_text or len(section_text.strip()) < 10:
            return True
        
        # Sections with only placeholders
        if section_text.strip() in ['[VOLATILE_DATA]', 'N/A', 'Not available']:
            return True
        
        return False
    
    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences, preserving numeric facts"""
        # Common sentence endings
        sentence_endings = r'(?<=[.!?])\s+'
        
        # Split but preserve numeric facts (don't split numbers with %, ₹, etc.)
        sentences = []
        current_sentence = ""
        
        for part in re.split(sentence_endings, text):
            if part.strip():
                # Check if this part ends with a numeric fact
                if re.search(r'\d+%|\d+₹|\d+\s*(?:cr|lakh|thousand)', part):
                    current_sentence += part + " "
                else:
                    if current_sentence.strip():
                        sentences.append(current_sentence.strip())
                    current_sentence = part + " "
        
        # Add the last sentence if exists
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return sentences
    
    def preserve_table_rows(self, text: str) -> List[str]:
        """Preserve table row structure for financial data"""
        # Look for table-like patterns
        table_pattern = r'([^:]+):\s*([^,]+)'
        matches = re.findall(table_pattern, text)
        
        if matches and len(matches) > 1:
            # This looks like tabular data
            rows = []
            for key, value in matches:
                rows.append(f"{key}: {value.strip()}")
            return rows
        
        # If no clear table structure, return as single chunk
        return [text]
    
    def split_long_section(self, section_name: str, text: str) -> List[str]:
        """Split a section that exceeds token limits"""
        token_count = self.estimate_token_count(text)
        
        if token_count <= self.soft_cap:
            return [text]
        
        # For financial sections, try to preserve table structure
        if any(keyword in section_name.lower() for keyword in ['expense', 'ratio', 'minimum', 'investment']):
            table_rows = self.preserve_table_rows(text)
            if len(table_rows) > 1:
                return table_rows
        
        # For other sections, split by sentences
        sentences = self.split_sentences(text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            test_tokens = self.estimate_token_count(test_chunk)
            
            if test_tokens <= self.hard_cap:
                current_chunk = test_chunk
            else:
                # Save current chunk and start new one
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def merge_short_sections(self, sections: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Merge sections under 50 tokens with related content"""
        merged_sections = []
        current_merge = []
        current_tokens = 0
        
        for section_name, section_text in sections:
            token_count = self.estimate_token_count(section_text)
            
            if token_count < self.min_token_threshold and current_merge:
                # Try to merge with current group
                if current_tokens + token_count <= self.soft_cap:
                    current_merge.append((section_name, section_text))
                    current_tokens += token_count
                else:
                    # Save current group and start new one
                    if current_merge:
                        merged_name = f"Merged: {', '.join([name for name, _ in current_merge])}"
                        merged_text = " ".join([text for _, text in current_merge])
                        merged_sections.append((merged_name, merged_text))
                    current_merge = [(section_name, section_text)]
                    current_tokens = token_count
            else:
                # Save any pending merge and start fresh
                if current_merge:
                    merged_name = f"Merged: {', '.join([name for name, _ in current_merge])}"
                    merged_text = " ".join([text for _, text in current_merge])
                    merged_sections.append((merged_name, merged_text))
                    current_merge = []
                    current_tokens = 0
                
                merged_sections.append((section_name, section_text))
        
        # Add any remaining merged group
        if current_merge:
            merged_name = f"Merged: {', '.join([name for name, _ in current_merge])}"
            merged_text = " ".join([text for _, text in current_merge])
            merged_sections.append((merged_name, merged_text))
        
        return merged_sections
    
    def create_chunks(self, doc: CleanedDoc) -> List[Chunk]:
        """Create chunks from a cleaned document"""
        chunks = []
        chunk_order = 0
        
        # Filter out empty sections
        valid_sections = []
        for section_name, section_info in doc.sections.items():
            section_text = section_info.get('text', '')
            if not self.is_empty_section(section_name, section_text):
                valid_sections.append((section_name, section_text))
        
        # Merge short sections
        merged_sections = self.merge_short_sections(valid_sections)
        
        # Process each section
        for section_name, section_text in merged_sections:
            # Split long sections if needed
            section_chunks = self.split_long_section(section_name, section_text)
            
            for chunk_text in section_chunks:
                # Calculate hashes
                content_hash = hashlib.sha256(chunk_text.encode()).hexdigest()
                
                # Create chunk
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    scheme_id=doc.scheme_id,
                    scheme_name=self.get_scheme_name(doc.scheme_id),
                    source_url=doc.source_url,
                    section=section_name,
                    text=chunk_text,
                    token_count=self.estimate_token_count(chunk_text),
                    chunk_order=chunk_order,
                    content_hash=content_hash,
                    stable_content_hash=doc.stable_content_hash,
                    last_updated=doc.fetched_at
                )
                
                chunks.append(chunk)
                chunk_order += 1
        
        logger.info(f"Created {len(chunks)} chunks from {doc.scheme_id}")
        return chunks
    
    def get_scheme_name(self, scheme_id: str) -> str:
        """Get scheme name from scheme ID"""
        scheme_names = {
            'hdfc_mid_cap': 'HDFC Mid Cap Fund - Direct Growth',
            'hdfc_equity': 'HDFC Equity Fund - Direct Growth',
            'hdfc_focused': 'HDFC Focused Fund - Direct Growth',
            'hdfc_elss': 'HDFC ELSS Tax Saver - Direct Plan Growth',
            'hdfc_large_cap': 'HDFC Large Cap Fund - Direct Growth'
        }
        return scheme_names.get(scheme_id, scheme_id)
    
    def save_chunks(self, chunks: List[Chunk]) -> bool:
        """Save chunks to JSON file"""
        try:
            if not chunks:
                logger.warning("No chunks to save")
                return False
            
            # Create output directory for scheme
            scheme_dir = os.path.join(self.output_dir, chunks[0].scheme_id)
            os.makedirs(scheme_dir, exist_ok=True)
            
            # Convert chunks to dict format
            chunks_data = []
            for chunk in chunks:
                chunk_dict = {
                    'chunk_id': chunk.chunk_id,
                    'scheme_id': chunk.scheme_id,
                    'scheme_name': chunk.scheme_name,
                    'source_url': chunk.source_url,
                    'section': chunk.section,
                    'last_updated': chunk.last_updated,
                    'content_hash': chunk.content_hash,
                    'stable_content_hash': chunk.stable_content_hash,
                    'text': chunk.text,
                    'token_count': chunk.token_count,
                    'chunk_order': chunk.chunk_order
                }
                chunks_data.append(chunk_dict)
            
            # Save to JSON file
            output_file = os.path.join(scheme_dir, 'chunks.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(chunks_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(chunks)} chunks to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving chunks: {e}")
            return False
    
    def process_cleaned_file(self, cleaned_file_path: str) -> List[Chunk]:
        """Process a single cleaned file and create chunks"""
        try:
            # Read cleaned document
            with open(cleaned_file_path, 'r', encoding='utf-8') as f:
                cleaned_data = json.load(f)
            
            # Create CleanedDoc object
            doc = CleanedDoc(
                scheme_id=cleaned_data.get('scheme_id'),
                source_url=cleaned_data.get('source_url'),
                fetched_at=cleaned_data.get('fetched_at'),
                sections=cleaned_data.get('sections', {}),
                must_have_anchors=cleaned_data.get('must_have_anchors', {}),
                extraction_health=cleaned_data.get('extraction_health', 'ok'),
                stable_content_hash=cleaned_data.get('stable_content_hash')
            )
            
            # Create chunks
            chunks = self.create_chunks(doc)
            
            # Save chunks
            if self.save_chunks(chunks):
                logger.info(f"Successfully processed {cleaned_file_path}")
                return chunks
            else:
                logger.error(f"Failed to save chunks from {cleaned_file_path}")
                return []
                
        except Exception as e:
            logger.error(f"Error processing cleaned file {cleaned_file_path}: {e}")
            return []
    
    def chunk_all(self) -> List[Chunk]:
        """Chunk all cleaned documents in the input directory"""
        logger.info("Starting chunking of all cleaned documents")
        
        all_chunks = []
        
        # Find all cleaned files
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                if file.endswith('cleaned.json'):
                    cleaned_file_path = os.path.join(root, file)
                    chunks = self.process_cleaned_file(cleaned_file_path)
                    all_chunks.extend(chunks)
        
        # Log summary
        successful_chunkings = len(set(chunk.scheme_id for chunk in all_chunks))
        total_schemes = len([d for d in os.listdir(self.output_dir) if os.path.isdir(os.path.join(self.output_dir, d))])
        
        logger.info(f"Chunking completed: {successful_chunkings}/{total_schemes} schemes, {len(all_chunks)} total chunks")
        
        return all_chunks
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the chunker"""
        try:
            total_schemes = len([d for d in os.listdir(self.output_dir) if os.path.isdir(os.path.join(self.output_dir, d))])
            
            health_report = {
                'total_schemes': total_schemes,
                'successful_chunkings': 0,
                'failed_chunkings': 0,
                'total_chunks': 0,
                'last_chunking_time': None,
                'health': 'unknown'
            }
            
            max_mtime = 0.0
            
            # Check each scheme directory for chunk files
            for scheme_dir_name in os.listdir(self.output_dir):
                scheme_dir = os.path.join(self.output_dir, scheme_dir_name)
                if os.path.isdir(scheme_dir):
                    chunks_file = os.path.join(scheme_dir, 'chunks.json')
                    if os.path.exists(chunks_file):
                        health_report['successful_chunkings'] += 1
                        
                        # Load and validate chunks
                        with open(chunks_file, 'r') as f:
                            chunks = json.load(f)
                            health_report['total_chunks'] += len(chunks)
                            
                            # Validate chunk quality
                            for chunk in chunks:
                                token_count = chunk.get('token_count', 0)
                                if token_count > self.hard_cap or token_count < self.min_token_threshold:
                                    health_report['health'] = 'degraded'
                                    break
                        
                        # Track last chunking time
                        file_mtime = os.path.getmtime(chunks_file)
                        if file_mtime > max_mtime:
                            max_mtime = file_mtime
                    else:
                        health_report['failed_chunkings'] += 1
                else:
                    health_report['failed_chunkings'] += 1
            
            if max_mtime > 0:
                health_report['last_chunking_time'] = datetime.fromtimestamp(max_mtime, timezone.utc).isoformat()
            
            # Determine overall health
            if health_report['successful_chunkings'] == total_schemes:
                if health_report['health'] == 'unknown':
                    health_report['health'] = 'ok'
            elif health_report['successful_chunkings'] > 0:
                health_report['health'] = 'partial'
            else:
                health_report['health'] = 'failed'
            
            return health_report
            
        except Exception as e:
            logger.error(f"Error getting chunking health: {e}")
            return {'health': 'error', 'error': str(e)}


# CLI interface for standalone execution
async def main():
    """CLI interface for the chunker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Chunk cleaned documents into retrieval units')
    parser.add_argument('--config-dir', help='Configuration directory path')
    parser.add_argument('--input-dir', help='Input directory with cleaned files')
    parser.add_argument('--output-dir', help='Output directory for chunk files')
    parser.add_argument('--scheme-id', help='Chunk specific scheme only')
    
    args = parser.parse_args()
    
    chunker = Chunker(args.config_dir)
    
    if args.input_dir:
        chunker.input_dir = args.input_dir
    if args.output_dir:
        chunker.output_dir = args.output_dir
    
    if args.scheme_id:
        # Chunk specific scheme
        cleaned_file = os.path.join(chunker.input_dir, args.scheme_id, 'cleaned.json')
        if os.path.exists(cleaned_file):
            chunks = chunker.process_cleaned_file(cleaned_file)
            if chunks:
                print(f"Successfully chunked scheme {args.scheme_id}: {len(chunks)} chunks")
            else:
                print(f"Failed to chunk scheme {args.scheme_id}")
        else:
            print(f"Cleaned file not found for scheme {args.scheme_id}")
    else:
        # Chunk all schemes
        all_chunks = chunker.chunk_all()
        
        # Print summary
        health = chunker.get_health_status()
        print(f"\nChunking Summary:")
        print(f"Total schemes: {health['total_schemes']}")
        print(f"Successful: {health['successful_chunkings']}")
        print(f"Failed: {health['failed_chunkings']}")
        print(f"Total chunks: {health['total_chunks']}")
        print(f"Health: {health['health']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
